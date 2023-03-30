-- Target table for the orders_daily DAG, in the "analytics" database.
CREATE TABLE IF NOT EXISTS daily_revenue (
    day     date           NOT NULL,
    region  text           NOT NULL,
    orders  integer        NOT NULL,
    revenue numeric(14, 2) NOT NULL,
    PRIMARY KEY (day, region)
);
