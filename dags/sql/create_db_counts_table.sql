
CREATE TABLE dataset_counts (
    product     varchar NOT NULL,
    source      varchar NOT NULL,
    count       integer NOT NULL,
    recorded_at timestamp DEFAULT current_timestamp

);