package com.ubs.topaz.util.hibernate;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import java.sql.Connection;
import java.sql.SQLException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * HikariCP equivalent of the old c3p0 {@code DbLoginConnectionCustomizer}
 * (which extended {@code AbstractConnectionCustomizer}).
 *
 * BACKGROUND
 * ----------
 * The old c3p0 class hooked into {@code onAcquire(Connection, String)} —
 * fired once for every brand new physical connection — and called
 * {@code new DbUtils().login(connection)} to run the DB login stored
 * procedure (sp_dbaacc_login).
 *
 * HikariCP has no direct equivalent of {@code onAcquire()}. It does NOT
 * expose a per-connection Java callback hook the way c3p0's
 * ConnectionCustomizer did. The two supported ways to run logic on every
 * new physical connection in HikariCP are:
 *
 *   1. {@code HikariConfig.setConnectionInitSql(String)} — but this only
 *      accepts a STATIC SQL STRING, not arbitrary Java/JDBC logic. Since
 *      DbUtils.login() takes a Connection and likely executes a
 *      CallableStatement internally (not a single SQL string we can
 *      extract), this option does not fit as-is.
 *
 *   2. Wrap HikariDataSource and override getConnection() to run the
 *      same login logic on every connection obtained from the pool.
 *      This is the closest behavioural equivalent to onAcquire() and is
 *      the approach used below.
 *
 * IMPORTANT — BEHAVIOURAL DIFFERENCE TO VERIFY:
 * c3p0's onAcquire() fires once per NEW PHYSICAL connection (i.e. NOT on
 * every checkout from the pool — only when c3p0 actually opens a new
 * connection to the database). The override below, in contrast, fires
 * the login logic on EVERY getConnection() call — that is, every time
 * a connection is borrowed from the pool, whether it's a brand new
 * physical connection or a pooled one being reused.
 *
 * If sp_dbaacc_login is idempotent and cheap to call repeatedly, this is
 * safe and simpler. If it is NOT safe to call on every checkout (e.g. it
 * has side effects beyond authentication, or is expensive), you need a
 * different approach: track which physical connections have already been
 * initialised using an IdentityHashMap<Connection, Boolean> guarded by
 * the wrapper, and only call login() the first time a given physical
 * Connection object is seen. A skeleton for that stricter variant is
 * included as a comment at the bottom of this file.
 *
 * USAGE
 * -----
 * Replace your old c3p0 HikariConfig/DataSource construction with:
 *
 *   HikariConfig config = new HikariConfig();
 *   config.setJdbcUrl(...);
 *   config.setUsername(...);
 *   config.setPassword(...);
 *   config.setMaximumPoolSize(10);
 *   config.setMinimumIdle(2);
 *   config.setConnectionTimeout(30_000);
 *   config.setIdleTimeout(600_000);
 *   config.setMaxLifetime(1_800_000);
 *
 *   DbLoginHikariDataSource dataSource = new DbLoginHikariDataSource(config);
 *
 *   // Pass dataSource to Hibernate Configuration:
 *   hibernateConfig.setProperty("hibernate.connection.provider_class",
 *       "org.hibernate.hikaricp.internal.HikariCPConnectionProvider");
 *   // wire dataSource into the HikariCP provider per your existing
 *   // Configuration/SessionFactory setup pattern
 */
public class DbLoginHikariDataSource extends HikariDataSource {

    private static final Logger LOGGER = LoggerFactory.getLogger(DbLoginHikariDataSource.class);

    public DbLoginHikariDataSource(HikariConfig config) {
        super(config);
    }

    @Override
    public Connection getConnection() throws SQLException {
        Connection connection = super.getConnection();
        try {
            LOGGER.debug("Executing DB Login function (sp_dbaacc_login)");
            new DbUtils().login(connection);
        } catch (Exception e) {
            // DbUtils.login() throws a checked exception per your confirmation —
            // wrap it as SQLException so it propagates correctly through the
            // getConnection() contract, consistent with how the c3p0 version
            // let onAcquire()'s "throws Exception" propagate to the pool.
            throw new SQLException("DB login (sp_dbaacc_login) failed on connection acquire", e);
        }
        return connection;
    }
}

/*
 * ─────────────────────────────────────────────────────────────────────────
 * STRICTER VARIANT — only run login() once per physical connection
 * ─────────────────────────────────────────────────────────────────────────
 * Use this instead of the simple override above if sp_dbaacc_login must
 * NOT be re-run every time a pooled connection is checked out — only on
 * the first time a given physical Connection object is handed out by
 * the pool.
 *
 * import java.util.Collections;
 * import java.util.Map;
 * import java.util.WeakHashMap;
 *
 * public class DbLoginHikariDataSource extends HikariDataSource {
 *
 *     private static final Logger LOGGER = LoggerFactory.getLogger(DbLoginHikariDataSource.class);
 *
 *     // WeakHashMap so entries are GC'd when the underlying Connection is
 *     // closed/discarded by the pool — avoids unbounded growth.
 *     private final Map<Connection, Boolean> initialised =
 *         Collections.synchronizedMap(new WeakHashMap<>());
 *
 *     public DbLoginHikariDataSource(HikariConfig config) {
 *         super(config);
 *     }
 *
 *     @Override
 *     public Connection getConnection() throws SQLException {
 *         Connection connection = super.getConnection();
 *         if (initialised.putIfAbsent(connection, Boolean.TRUE) == null) {
 *             try {
 *                 LOGGER.debug("Executing DB Login function (sp_dbaacc_login) — first use of this physical connection");
 *                 new DbUtils().login(connection);
 *             } catch (Exception e) {
 *                 initialised.remove(connection);
 *                 throw new SQLException("DB login (sp_dbaacc_login) failed on connection acquire", e);
 *             }
 *         }
 *         return connection;
 *     }
 * }
 *
 * NOTE: HikariCP wraps the physical Connection in a proxy, and a new proxy
 * object may be returned by getConnection() on each checkout even when the
 * underlying physical connection is reused from the pool. If that's the
 * case in your HikariCP version, the WeakHashMap<Connection, Boolean> keyed
 * on the proxy will NOT correctly detect "same physical connection" across
 * checkouts — it would behave the same as the simple variant above. To
 * reliably key on the physical connection, you'd need to unwrap the proxy
 * (Connection.unwrap(...) or similar) before using it as the map key.
 * VERIFY this behaviour against your HikariCP version before relying on
 * the stricter variant for correctness.
 */
