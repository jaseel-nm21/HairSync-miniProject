"""
HairSync Database Initializer Script
Creates SQLite database, executes hairsync.sql schema,
and ensures admin and seed accounts are properly seeded.
Usage: python -m database.init_db OR python database/init_db.py OR flask init-db
"""

import os
import sys
from pathlib import Path
import sqlite3
from werkzeug.security import generate_password_hash

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config


def run_init(db_path=None):
    """Initializes the SQLite database with tables and seed data."""
    if db_path is None:
        db_path = Config.DATABASE

    print("=" * 60)
    print("HairSync Database Initialization (SQLite)")
    print("=" * 60)
    print(f"[*] Target database file: {db_path}")

    # Ensure target directory exists
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    sql_path = BASE_DIR / 'database' / 'hairsync.sql'
    if not sql_path.exists():
        print(f"[-] ERROR: SQL schema file not found at {sql_path}")
        sys.exit(1)

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        print("[*] Executing database schema...")
        conn.executescript(sql_content)

        # Update initial user seeds with live Werkzeug password hashes
        print("[*] Generating secure password hashes for seed accounts...")
        admin_hash = generate_password_hash("Admin@123")
        sample_hash = generate_password_hash("Password@123")

        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = ? WHERE email = 'admin@hairsync.com'", (admin_hash,))
        cur.execute("UPDATE users SET password_hash = ? WHERE email != 'admin@hairsync.com'", (sample_hash,))
        conn.commit()
        conn.close()

        print("[+] SQLite database initialized and synced successfully.")
    except sqlite3.Error as e:
        print(f"[-] ERROR during database initialization: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Database `hairsync.db` initialized successfully!")
    print("Default Test Accounts:")
    print("  1. Admin        : admin@hairsync.com      / Admin@123")
    print("  2. Approved NGO : contact@hopehair.org  / Password@123")
    print("  3. Pending NGO  : info@gracecrown.org   / Password@123")
    print("  4. Donor        : donor@example.com       / Password@123")
    print("  5. Recipient    : recipient@example.com   / Password@123")
    print("=" * 60)


def init_db_if_needed(db_path=None):
    """Automatically initialize the database or apply missing schema updates."""
    if db_path is None:
        db_path = Config.DATABASE
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        run_init(db_path)
    else:
        # Check and apply non-destructive table migrations (Module 2 donation_centers)
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA foreign_keys = ON;")
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='donation_centers'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating donation_centers table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS donation_centers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ngo_id INTEGER NOT NULL,
                        center_name TEXT NOT NULL,
                        address TEXT NOT NULL,
                        district TEXT NOT NULL,
                        city TEXT NOT NULL,
                        state TEXT NOT NULL DEFAULT 'Kerala',
                        pincode TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        email TEXT DEFAULT NULL,
                        opening_time TEXT NOT NULL,
                        closing_time TEXT NOT NULL,
                        working_days TEXT NOT NULL,
                        description TEXT DEFAULT NULL,
                        latitude REAL DEFAULT NULL,
                        longitude REAL DEFAULT NULL,
                        status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive', 'Pending', 'Rejected', 'Approved')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE CASCADE
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dc_ngo ON donation_centers(ngo_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dc_district ON donation_centers(district);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dc_status ON donation_centers(status);")
                # Insert default seed center if ngo_profiles has id 1
                cur.execute("SELECT id FROM ngo_profiles WHERE id = 1")
                if cur.fetchone():
                    cur.execute("""
                        INSERT OR IGNORE INTO donation_centers 
                        (id, ngo_id, center_name, address, district, city, state, pincode, phone, email, opening_time, closing_time, working_days, description, latitude, longitude, status)
                        VALUES (1, 1, 'Kochi Central Hair Drop Center', '45 Healthcare Boulevard, Near City Hospital, Marine Drive', 'Ernakulam', 'Kochi', 'Kerala', '682031', '+91 9876543210', 'kochi.center@hopehair.org', '09:00', '17:00', 'Monday - Saturday', 'Primary collection hub accepting sanitized hair donations, measurements, and donor consultations.', 9.9816, 76.2799, 'Active');
                    """)
                conn.commit()

            # Module 3 migrations: donation_guidelines, appointments, donations
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='donation_guidelines'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating donation_guidelines table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS donation_guidelines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ngo_id INTEGER NOT NULL UNIQUE,
                        minimum_hair_length REAL NOT NULL DEFAULT 20.0,
                        allowed_hair_types TEXT NOT NULL DEFAULT 'Straight,Wavy,Curly,Coily',
                        allow_colored_hair TEXT NOT NULL DEFAULT 'Requires Review' CHECK(allow_colored_hair IN ('Allowed', 'Requires Review', 'Not Allowed')),
                        allow_chemically_treated TEXT NOT NULL DEFAULT 'Not Allowed' CHECK(allow_chemically_treated IN ('Allowed', 'Requires Review', 'Not Allowed')),
                        allow_bleached_hair TEXT NOT NULL DEFAULT 'Not Allowed' CHECK(allow_bleached_hair IN ('Allowed', 'Requires Review', 'Not Allowed')),
                        minimum_condition TEXT DEFAULT 'Clean, dry, tied in ponytail or braid',
                        additional_requirements TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE CASCADE
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dg_ngo ON donation_guidelines(ngo_id);")
                cur.execute("SELECT id FROM ngo_profiles WHERE id = 1")
                if cur.fetchone():
                    cur.execute("""
                        INSERT OR IGNORE INTO donation_guidelines 
                        (id, ngo_id, minimum_hair_length, allowed_hair_types, allow_colored_hair, allow_chemically_treated, allow_bleached_hair, minimum_condition, additional_requirements)
                        VALUES (1, 1, 20.0, 'Straight,Wavy,Curly,Coily', 'Requires Review', 'Not Allowed', 'Not Allowed', 'Clean, dry, washed within 24 hours, tied in ponytail or braid at both ends', 'Layered hair is accepted if longest layer meets minimum length. Gray hair is welcome.');
                    """)
                conn.commit()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating appointments table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        donor_id INTEGER NOT NULL,
                        ngo_id INTEGER NOT NULL,
                        donation_center_id INTEGER NOT NULL,
                        appointment_date TEXT NOT NULL,
                        appointment_time TEXT NOT NULL,
                        purpose TEXT DEFAULT 'Hair Donation',
                        donor_notes TEXT DEFAULT NULL,
                        ngo_notes TEXT DEFAULT NULL,
                        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Confirmed', 'Rejected', 'Cancelled', 'Completed', 'No Show')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (donor_id) REFERENCES donor_profiles (id) ON DELETE CASCADE,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE CASCADE,
                        FOREIGN KEY (donation_center_id) REFERENCES donation_centers (id) ON DELETE CASCADE
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_appt_donor ON appointments(donor_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_appt_ngo ON appointments(ngo_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_appt_center ON appointments(donation_center_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_appt_date ON appointments(appointment_date);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_appt_status ON appointments(status);")
                conn.commit()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='donations'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating donations table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS donations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        donor_id INTEGER NOT NULL,
                        ngo_id INTEGER NOT NULL,
                        donation_center_id INTEGER NOT NULL,
                        appointment_id INTEGER UNIQUE DEFAULT NULL,
                        hair_length REAL NOT NULL,
                        hair_type TEXT NOT NULL,
                        hair_condition TEXT NOT NULL,
                        donation_date TEXT NOT NULL,
                        quantity_or_estimated_weight TEXT DEFAULT NULL,
                        notes TEXT DEFAULT NULL,
                        status TEXT NOT NULL DEFAULT 'Completed' CHECK(status IN ('Completed', 'Recorded', 'Rejected')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (donor_id) REFERENCES donor_profiles (id) ON DELETE CASCADE,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE CASCADE,
                        FOREIGN KEY (donation_center_id) REFERENCES donation_centers (id) ON DELETE CASCADE,
                        FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE SET NULL
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_don_donor ON donations(donor_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_don_ngo ON donations(ngo_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_don_center ON donations(donation_center_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_don_appt ON donations(appointment_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_don_date ON donations(donation_date);")
                conn.commit()

            conn.close()
        except Exception as e:
            print(f"[-] Migration check warning: {e}")


if __name__ == '__main__':
    run_init()

