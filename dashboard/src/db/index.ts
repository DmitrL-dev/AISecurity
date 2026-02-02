/**
 * Database connection
 */

import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema/index";

// Connection string from environment
const connectionString = process.env.DATABASE_URL;

// Create postgres client
const client = connectionString 
  ? postgres(connectionString)
  : null;

// Create drizzle instance
export const db = client ? drizzle(client, { schema }) : null;

/**
 * Get database instance (throws if not configured)
 */
export function getDb() {
  if (!db) {
    throw new Error("Database not configured. Set DATABASE_URL environment variable.");
  }
  return db;
}

// Export type for use in other files
export type Database = NonNullable<typeof db>;
