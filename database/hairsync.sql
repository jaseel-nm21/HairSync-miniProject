-- ==========================================================
-- HairSync: Web-Based Hair Donor and Recipient Management Platform
-- Database Schema for Module 1 (SQLite Compatible)
-- ==========================================================

-- Enable Foreign Key support
PRAGMA foreign_keys = ON;

-- 1. USERS TABLE
-- Stores credentials and user role information
DROP TABLE IF EXISTS wig_tracking_logs;
DROP TABLE IF EXISTS wig_requests;
DROP TABLE IF EXISTS wigs;
DROP TABLE IF EXISTS hair_inventory;
DROP TABLE IF EXISTS donations;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS donation_guidelines;
DROP TABLE IF EXISTS donation_centers;
DROP TABLE IF EXISTS recipient_profiles;
DROP TABLE IF EXISTS ngo_profiles;
DROP TABLE IF EXISTS donor_profiles;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'ngo', 'donor', 'recipient')),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'pending', 'suspended')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);

-- 2. DONOR PROFILES TABLE
-- Stores donor-specific health and hair profile details
CREATE TABLE donor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    district TEXT NOT NULL,
    hair_length REAL DEFAULT NULL,
    hair_type TEXT DEFAULT NULL,
    hair_condition TEXT DEFAULT NULL,
    photo TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 3. NGO PROFILES TABLE
-- Stores verified organization profiles and administration approval states
CREATE TABLE ngo_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    organization_name TEXT NOT NULL,
    registration_number TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT NOT NULL,
    district TEXT NOT NULL,
    description TEXT DEFAULT NULL,
    approval_status TEXT DEFAULT 'pending' CHECK(approval_status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ngo_approval ON ngo_profiles(approval_status);

-- 4. RECIPIENT PROFILES TABLE
-- Stores recipient health/reason details for medical wig allocation
CREATE TABLE recipient_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    district TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    reason_for_wig TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 5. DONATION CENTERS TABLE (Module 2)
-- Stores physical donation collection hubs managed by verified NGOs
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

CREATE INDEX IF NOT EXISTS idx_dc_ngo ON donation_centers(ngo_id);
CREATE INDEX IF NOT EXISTS idx_dc_district ON donation_centers(district);
CREATE INDEX IF NOT EXISTS idx_dc_status ON donation_centers(status);

-- ==========================================================
-- MODULE 3: ELIGIBILITY, DONATIONS & APPOINTMENTS
-- ==========================================================

-- 6. DONATION GUIDELINES TABLE (Module 3)
-- Allows each NGO to define their specific hair donation criteria
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

CREATE INDEX IF NOT EXISTS idx_dg_ngo ON donation_guidelines(ngo_id);

-- 7. APPOINTMENTS TABLE (Module 3)
-- Handles scheduling of physical or collection appointments
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

CREATE INDEX IF NOT EXISTS idx_appt_donor ON appointments(donor_id);
CREATE INDEX IF NOT EXISTS idx_appt_ngo ON appointments(ngo_id);
CREATE INDEX IF NOT EXISTS idx_appt_center ON appointments(donation_center_id);
CREATE INDEX IF NOT EXISTS idx_appt_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appt_status ON appointments(status);

-- 8. DONATIONS TABLE (Module 3)
-- Permanent hair donation records recorded upon fulfillment
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

CREATE INDEX IF NOT EXISTS idx_don_donor ON donations(donor_id);
CREATE INDEX IF NOT EXISTS idx_don_ngo ON donations(ngo_id);
CREATE INDEX IF NOT EXISTS idx_don_center ON donations(donation_center_id);
CREATE INDEX IF NOT EXISTS idx_don_appt ON donations(appointment_id);
CREATE INDEX IF NOT EXISTS idx_don_date ON donations(donation_date);


-- ==========================================================
-- MODULE 4: HAIR & WIG INVENTORY MANAGEMENT
-- ==========================================================

-- 9. HAIR INVENTORY TABLE
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

CREATE INDEX IF NOT EXISTS idx_hi_ngo ON hair_inventory(ngo_id);
CREATE INDEX IF NOT EXISTS idx_hi_status ON hair_inventory(status);

-- 10. WIGS INVENTORY TABLE
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

CREATE INDEX IF NOT EXISTS idx_wig_ngo ON wigs(ngo_id);
CREATE INDEX IF NOT EXISTS idx_wig_status ON wigs(status);


-- ==========================================================
-- MODULE 5 & 6: RECIPIENT WIG REQUESTS & STATUS TRACKING
-- ==========================================================

-- 11. WIG REQUESTS TABLE
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

CREATE INDEX IF NOT EXISTS idx_wr_recipient ON wig_requests(recipient_id);
CREATE INDEX IF NOT EXISTS idx_wr_ngo ON wig_requests(ngo_id);
CREATE INDEX IF NOT EXISTS idx_wr_status ON wig_requests(status);

-- 12. WIG TRACKING LOGS TABLE
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

CREATE INDEX IF NOT EXISTS idx_wtl_request ON wig_tracking_logs(wig_request_id);


-- ==========================================================
-- INITIAL SAMPLE DATA & DEFAULT SEEDS
-- Default accounts:
-- 1. Admin     : admin@hairsync.com      / Admin@123
-- 2. Approved NGO: contact@hopehair.org  / Password@123
-- 3. Pending NGO : info@gracecrown.org   / Password@123
-- 4. Donor     : donor@example.com       / Password@123
-- 5. Recipient : recipient@example.com   / Password@123
-- Note: Password hashes are generated dynamically by init_db.py
-- ==========================================================

-- 1. Default Admin (Password: Admin@123)
INSERT INTO users (id, name, email, password_hash, role, status) VALUES
(1, 'System Administrator', 'admin@hairsync.com', 'scrypt:32768:8:1$placeholder$admin', 'admin', 'active');

-- 2. Sample Approved NGO (Password: Password@123)
INSERT INTO users (id, name, email, password_hash, role, status) VALUES
(2, 'Hope Hair Foundation', 'contact@hopehair.org', 'scrypt:32768:8:1$placeholder$sample', 'ngo', 'active');

INSERT INTO ngo_profiles (user_id, organization_name, registration_number, phone, email, address, district, description, approval_status) VALUES
(2, 'Hope Hair Foundation', 'NGO-IND-2021-9874', '+91 9876543210', 'contact@hopehair.org', '45 Healthcare Boulevard, Near City Hospital', 'Ernakulam', 'Non-profit dedicated to manufacturing natural human-hair wigs for underprivileged cancer patients and medical hair loss survivors.', 'approved');

-- 3. Sample Pending NGO (Password: Password@123)
INSERT INTO users (id, name, email, password_hash, role, status) VALUES
(3, 'Grace Crown Care', 'info@gracecrown.org', 'scrypt:32768:8:1$placeholder$sample', 'ngo', 'pending');

INSERT INTO ngo_profiles (user_id, organization_name, registration_number, phone, email, address, district, description, approval_status) VALUES
(3, 'Grace Crown Care', 'REG-KL-88321-2023', '+91 9845012345', 'info@gracecrown.org', '12 Greenfield Road, West Wing', 'Kozhikode', 'Community initiative supporting young pediatric chemotherapy patients with customized cranial prostheses.', 'pending');

-- 4. Sample Donor (Password: Password@123)
INSERT INTO users (id, name, email, password_hash, role, status) VALUES
(4, 'Ananya Sharma', 'donor@example.com', 'scrypt:32768:8:1$placeholder$sample', 'donor', 'active');

INSERT INTO donor_profiles (user_id, phone, address, district, hair_length, hair_type, hair_condition, photo) VALUES
(4, '+91 9123456789', 'Apartment 4B, Silver Heights, Marine Drive', 'Ernakulam', 14.50, 'Wavy', 'Virgin/Untreated', NULL);

-- 5. Sample Recipient (Password: Password@123)
INSERT INTO users (id, name, email, password_hash, role, status) VALUES
(5, 'Meera Nair', 'recipient@example.com', 'scrypt:32768:8:1$placeholder$sample', 'recipient', 'active');

INSERT INTO recipient_profiles (user_id, phone, address, district, date_of_birth, reason_for_wig) VALUES
(5, '+91 9988776655', 'House No 23, Rose Gardens, Kowdiar', 'Thiruvananthapuram', '1998-05-14', 'Undergoing chemotherapy treatment for breast cancer. Requesting natural wig for emotional confidence.');

-- 6. Sample Donation Center for Hope Hair Foundation (ngo_id = 1)
INSERT INTO donation_centers (id, ngo_id, center_name, address, district, city, state, pincode, phone, email, opening_time, closing_time, working_days, description, latitude, longitude, status) VALUES
(1, 1, 'Kochi Central Hair Drop Center', '45 Healthcare Boulevard, Near City Hospital, Marine Drive', 'Ernakulam', 'Kochi', 'Kerala', '682031', '+91 9876543210', 'kochi.center@hopehair.org', '09:00', '17:00', 'Monday - Saturday', 'Primary collection hub accepting sanitized hair donations, measurements, and donor consultations.', 9.9816, 76.2799, 'Active');

-- 7. Sample Donation Guidelines for Hope Hair Foundation (ngo_id = 1)
INSERT INTO donation_guidelines (id, ngo_id, minimum_hair_length, allowed_hair_types, allow_colored_hair, allow_chemically_treated, allow_bleached_hair, minimum_condition, additional_requirements) VALUES
(1, 1, 20.0, 'Straight,Wavy,Curly,Coily', 'Requires Review', 'Not Allowed', 'Not Allowed', 'Clean, dry, washed within 24 hours, tied in ponytail or braid at both ends', 'Layered hair is accepted if longest layer meets minimum length. Gray hair is welcome.');

-- 8. Sample Hair Inventory for Hope Hair Foundation (ngo_id = 1)
INSERT INTO hair_inventory (id, ngo_id, donation_id, hair_type, hair_length, hair_condition, quantity_or_weight, status, notes) VALUES
(1, 1, NULL, 'Straight', 32.0, 'Virgin / Untreated', '180 grams', 'In Stock', 'Sanitized high-grade straight hair bundle suitable for medium wigs.'),
(2, 1, NULL, 'Wavy', 28.5, 'Virgin / Untreated', '150 grams', 'In Processing', 'Currently in sorting and sanitization process.');

-- 9. Sample Wigs Inventory for Hope Hair Foundation (ngo_id = 1)
INSERT INTO wigs (id, ngo_id, wig_type, hair_source, hair_color, hair_length, size, condition, status, notes) VALUES
(1, 1, 'Medium Wavy Crown', 'Natural', 'Natural Dark Brown', 30.0, 'Medium', 'New / Sanitized', 'Available', '100% natural human hair wig with breathable lightweight cap, designed for sensitive scalps.'),
(2, 1, 'Short Classic Bob', 'Natural', 'Natural Jet Black', 22.0, 'Small', 'New / Sanitized', 'Available', 'Crafted for pediatric cancer patients or small head circumference, soft perimeter tape.');

-- 10. Sample Wig Request from Meera Nair (recipient_id = 1)
INSERT INTO wig_requests (id, recipient_id, ngo_id, assigned_wig_id, preferred_wig_type, hair_source, preferred_length, preferred_color, preferred_size, reason_for_request, delivery_address, delivery_city, delivery_district, delivery_pincode, contact_phone, additional_notes, status) VALUES
(1, 1, 1, NULL, 'Medium Wavy Crown', 'Natural', 30.0, 'Natural Dark Brown', 'Medium', 'Undergoing chemotherapy for breast cancer; seeking natural wig for emotional well-being.', 'House No 23, Rose Gardens, Kowdiar', 'Thiruvananthapuram', 'Thiruvananthapuram', '695003', '+91 9988776655', 'Prefer lightweight inner mesh if possible.', 'Under Review');

-- 11. Sample Wig Tracking Logs for Request #1
INSERT INTO wig_tracking_logs (wig_request_id, status, remarks, updated_by_user_id) VALUES
(1, 'Submitted', 'Recipient submitted request for natural-hair wig.', 5),
(1, 'Under Review', 'Application received and currently under medical verification by Hope Hair Foundation.', 2);


