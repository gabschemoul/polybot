-- PolyBot Supabase Schema
-- Run this in your Supabase SQL Editor to create the required tables

-- Simulations table
CREATE TABLE IF NOT EXISTS simulations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data JSONB NOT NULL
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_simulations_created_at ON simulations(created_at DESC);

-- Insights table
CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_insights_created_at ON insights(created_at DESC);

-- Experiments table
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC);

-- Enable Row Level Security (optional but recommended)
-- This allows all users to read/write for now (public access)
ALTER TABLE simulations ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all operations for authenticated and anonymous users
CREATE POLICY "Allow all access to simulations" ON simulations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to insights" ON insights FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to experiments" ON experiments FOR ALL USING (true) WITH CHECK (true);
