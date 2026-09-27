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

            # Module 4: hair_inventory
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hair_inventory'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating hair_inventory table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS hair_inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ngo_id INTEGER NOT NULL,
                        donation_id INTEGER UNIQUE DEFAULT NULL,
                        hair_type TEXT NOT NULL,
                        hair_length REAL NOT NULL,
                        hair_condition TEXT NOT NULL,
                        quantity_or_weight TEXT DEFAULT NULL,
                        status TEXT NOT NULL DEFAULT 'In Stock' CHECK(status IN ('In Stock', 'In Processing', 'Used in Wig', 'Disposed')),
                        notes TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE CASCADE,
                        FOREIGN KEY (donation_id) REFERENCES donations (id) ON DELETE SET NULL
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_hi_ngo ON hair_inventory(ngo_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_hi_status ON hair_inventory(status);")
                cur.execute("SELECT id FROM ngo_profiles WHERE id = 1")
                if cur.fetchone():
                    cur.execute("""
                        INSERT OR IGNORE INTO hair_inventory (id, ngo_id, donation_id, hair_type, hair_length, hair_condition, quantity_or_weight, status, notes)
                        VALUES 
                        (1, 1, NULL, 'Straight', 32.0, 'Virgin / Untreated', '180 grams', 'In Stock', 'Sanitized high-grade straight hair bundle.'),
                        (2, 1, NULL, 'Wavy', 28.5, 'Virgin / Untreated', '150 grams', 'In Processing', 'Currently in sorting and sanitization.');
                    """)
                conn.commit()

            # Module 4: wigs
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wigs'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating wigs table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wigs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ngo_id INTEGER NOT NULL,
                        wig_type TEXT NOT NULL,
                        hair_source TEXT NOT NULL DEFAULT 'Natural' CHECK(hair_source IN ('Natural', 'Synthetic', 'Blend')),
                        hair_color TEXT NOT NULL,
                        hair_length REAL NOT NULL,
                        size TEXT NOT NULL DEFAULT 'Medium' CHECK(size IN ('Small', 'Medium', 'Large', 'Adjustable')),
                        condition TEXT NOT NULL DEFAULT 'New / Sanitized',
                        status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Assigned', 'In Preparation', 'Dispatched', 'Delivered')),
                        notes TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE CASCADE
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wig_ngo ON wigs(ngo_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wig_status ON wigs(status);")
                cur.execute("SELECT id FROM ngo_profiles WHERE id = 1")
                if cur.fetchone():
                    cur.execute("""
                        INSERT OR IGNORE INTO wigs (id, ngo_id, wig_type, hair_source, hair_color, hair_length, size, condition, status, notes)
                        VALUES
                        (1, 1, 'Medium Wavy Crown', 'Natural', 'Natural Dark Brown', 30.0, 'Medium', 'New / Sanitized', 'Available', '100% natural human hair wig with breathable lightweight cap.'),
                        (2, 1, 'Short Classic Bob', 'Natural', 'Natural Jet Black', 22.0, 'Small', 'New / Sanitized', 'Available', 'Crafted for pediatric chemotherapy patients with soft perimeter tape.');
                    """)
                conn.commit()

            # Module 5: wig_requests
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wig_requests'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating wig_requests table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wig_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recipient_id INTEGER NOT NULL,
                        ngo_id INTEGER DEFAULT NULL,
                        assigned_wig_id INTEGER UNIQUE DEFAULT NULL,
                        preferred_wig_type TEXT NOT NULL,
                        hair_source TEXT NOT NULL DEFAULT 'Natural',
                        preferred_length REAL NOT NULL,
                        preferred_color TEXT NOT NULL,
                        preferred_size TEXT NOT NULL DEFAULT 'Medium',
                        reason_for_request TEXT NOT NULL,
                        delivery_address TEXT NOT NULL,
                        delivery_city TEXT NOT NULL,
                        delivery_district TEXT NOT NULL,
                        delivery_pincode TEXT NOT NULL,
                        contact_phone TEXT NOT NULL,
                        additional_notes TEXT DEFAULT NULL,
                        status TEXT NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'Under Review', 'Approved', 'Rejected', 'Wig Assigned', 'Preparing', 'Ready for Dispatch', 'Dispatched', 'In Transit', 'Out for Delivery', 'Delivered')),
                        rejection_reason TEXT DEFAULT NULL,
                        tracking_number TEXT DEFAULT NULL,
                        courier_service TEXT DEFAULT NULL,
                        estimated_delivery_date TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (recipient_id) REFERENCES recipient_profiles (id) ON DELETE CASCADE,
                        FOREIGN KEY (ngo_id) REFERENCES ngo_profiles (id) ON DELETE SET NULL,
                        FOREIGN KEY (assigned_wig_id) REFERENCES wigs (id) ON DELETE SET NULL
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wr_recipient ON wig_requests(recipient_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wr_ngo ON wig_requests(ngo_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wr_status ON wig_requests(status);")
                cur.execute("SELECT id FROM recipient_profiles WHERE id = 1")
                if cur.fetchone():
                    cur.execute("""
                        INSERT OR IGNORE INTO wig_requests (id, recipient_id, ngo_id, assigned_wig_id, preferred_wig_type, hair_source, preferred_length, preferred_color, preferred_size, reason_for_request, delivery_address, delivery_city, delivery_district, delivery_pincode, contact_phone, additional_notes, status)
                        VALUES
                        (1, 1, 1, NULL, 'Medium Wavy Crown', 'Natural', 30.0, 'Natural Dark Brown', 'Medium', 'Undergoing chemotherapy for breast cancer; requesting natural wig.', 'House No 23, Rose Gardens, Kowdiar', 'Thiruvananthapuram', 'Thiruvananthapuram', '695003', '+91 9988776655', 'Prefer lightweight inner mesh.', 'Under Review');
                    """)
                conn.commit()

            # Module 6: wig_tracking_logs
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wig_tracking_logs'")
            if not cur.fetchone():
                print("[*] Applying non-destructive migration: creating wig_tracking_logs table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wig_tracking_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wig_request_id INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        remarks TEXT DEFAULT NULL,
                        updated_by_user_id INTEGER DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (wig_request_id) REFERENCES wig_requests (id) ON DELETE CASCADE,
                        FOREIGN KEY (updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wtl_request ON wig_tracking_logs(wig_request_id);")
                cur.execute("SELECT id FROM wig_requests WHERE id = 1")
                if cur.fetchone():
                    cur.execute("""
                        INSERT OR IGNORE INTO wig_tracking_logs (wig_request_id, status, remarks, updated_by_user_id)
                        VALUES
                        (1, 'Submitted', 'Recipient submitted request for natural-hair wig.', 5),
                        (1, 'Under Review', 'Application received and currently under medical verification by Hope Hair Foundation.', 2);
                    """)
                conn.commit()

            conn.close()
        except Exception as e:
            print(f"[-] Migration check warning: {e}")


if __name__ == '__main__':
    run_init()

