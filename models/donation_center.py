"""
DonationCenter Model (Module 2)
Handles physical hair donation center operations, NGO ownership verification,
status management, and donor directory queries.
"""

from database.db import query_db, execute_db


class DonationCenter:
    @staticmethod
    def create(ngo_id, center_name, address, district, city,
               pincode='682001', phone='', opening_time='09:00', closing_time='17:00',
               working_days='Monday - Saturday', state='Kerala', email=None,
               description=None, latitude=None, longitude=None, status='Active', **kwargs):
        """
        Creates a new donation center affiliated with an approved NGO.
        Returns the created center ID.
        """
        # Handle case where state was passed as 6th positional arg
        if 'state' in kwargs:
            state = kwargs['state']
        if 'email' in kwargs:
            email = kwargs['email']

        sql = """
            INSERT INTO donation_centers 
            (ngo_id, center_name, address, district, city, state, pincode, phone,
             email, opening_time, closing_time, working_days, description, latitude, longitude, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            ngo_id,
            str(center_name).strip(),
            str(address).strip(),
            str(district).strip(),
            str(city).strip(),
            str(state).strip() if state else 'Kerala',
            str(pincode).strip(),
            str(phone).strip(),
            str(email).strip().lower() if email else None,
            str(opening_time).strip(),
            str(closing_time).strip(),
            str(working_days).strip(),
            str(description).strip() if description else None,
            float(latitude) if latitude is not None and latitude != '' else None,
            float(longitude) if longitude is not None and longitude != '' else None,
            status
        ))
        return res['lastrowid']


    @staticmethod
    def get_by_id(center_id):
        """Fetch single donation center with associated NGO details."""
        sql = """
            SELECT dc.*, 
                   np.organization_name as ngo_name,
                   np.registration_number as ngo_reg_no,
                   np.phone as ngo_phone,
                   np.email as ngo_email,
                   np.user_id as ngo_user_id
            FROM donation_centers dc
            JOIN ngo_profiles np ON dc.ngo_id = np.id
            WHERE dc.id = %s
        """
        return query_db(sql, (center_id,), one=True)

    @staticmethod
    def get_by_ngo_id(ngo_id, search=None, status=None):
        """Fetch all donation centers owned by a specific NGO."""
        conditions = ["ngo_id = %s"]
        params = [ngo_id]

        if status and status.lower() != 'all':
            conditions.append("LOWER(status) = %s")
            params.append(status.lower())

        if search:
            conditions.append("(LOWER(center_name) LIKE %s OR LOWER(district) LIKE %s OR LOWER(city) LIKE %s)")
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern])

        where_clause = " WHERE " + " AND ".join(conditions)
        sql = f"SELECT * FROM donation_centers {where_clause} ORDER BY created_at DESC"
        return query_db(sql, tuple(params))

    @staticmethod
    def get_all(status=None, district=None, search=None):
        """Fetch all donation centers with NGO metadata for Admin oversight."""
        conditions = []
        params = []

        if status and status.lower() != 'all':
            conditions.append("LOWER(dc.status) = %s")
            params.append(status.lower())

        if district and district.lower() != 'all':
            conditions.append("LOWER(dc.district) = %s")
            params.append(district.lower())

        if search:
            conditions.append(
                "(LOWER(dc.center_name) LIKE %s OR LOWER(dc.district) LIKE %s OR "
                "LOWER(dc.city) LIKE %s OR LOWER(np.organization_name) LIKE %s)"
            )
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT dc.*, 
                   np.organization_name as ngo_name,
                   np.registration_number as ngo_reg_no,
                   np.user_id as ngo_user_id
            FROM donation_centers dc
            JOIN ngo_profiles np ON dc.ngo_id = np.id
            {where_clause}
            ORDER BY dc.created_at DESC
        """
        return query_db(sql, tuple(params))

    @staticmethod
    def get_active_or_approved(district=None, search=None):
        """
        Fetch active or approved donation centers for public / donor directory view.
        Only verified operational centers are visible.
        """
        conditions = ["dc.status IN ('Active', 'Approved')"]
        params = []

        if district and district.lower() != 'all':
            conditions.append("LOWER(dc.district) = %s")
            params.append(district.lower())

        if search:
            conditions.append(
                "(LOWER(dc.center_name) LIKE %s OR LOWER(dc.district) LIKE %s OR "
                "LOWER(dc.city) LIKE %s OR LOWER(np.organization_name) LIKE %s)"
            )
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_clause = " WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT dc.*, 
                   np.organization_name as ngo_name,
                   np.registration_number as ngo_reg_no,
                   np.phone as ngo_phone
            FROM donation_centers dc
            JOIN ngo_profiles np ON dc.ngo_id = np.id
            {where_clause}
            ORDER BY dc.district ASC, dc.center_name ASC
        """
        return query_db(sql, tuple(params))

    @staticmethod
    def update(center_id, center_name, address, district, city, state, pincode,
               phone, email, opening_time, closing_time, working_days,
               description=None, latitude=None, longitude=None, status=None, ngo_id=None):
        """
        Updates a donation center.
        If ngo_id is provided, strictly enforces ownership (security isolation).
        """
        if ngo_id is not None:
            # Enforce ownership check
            center = DonationCenter.get_by_id(center_id)
            if not center or center['ngo_id'] != ngo_id:
                return False

        if status:
            sql = """
                UPDATE donation_centers
                SET center_name = %s, address = %s, district = %s, city = %s, state = %s,
                    pincode = %s, phone = %s, email = %s, opening_time = %s, closing_time = %s,
                    working_days = %s, description = %s, latitude = %s, longitude = %s, 
                    status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = (
                center_name.strip(), address.strip(), district.strip(), city.strip(),
                state.strip() if state else 'Kerala', pincode.strip(), phone.strip(),
                email.strip().lower() if email else None, opening_time.strip(), closing_time.strip(),
                working_days.strip(), description.strip() if description else None,
                float(latitude) if latitude is not None and latitude != '' else None,
                float(longitude) if longitude is not None and longitude != '' else None,
                status, center_id
            )
        else:
            sql = """
                UPDATE donation_centers
                SET center_name = %s, address = %s, district = %s, city = %s, state = %s,
                    pincode = %s, phone = %s, email = %s, opening_time = %s, closing_time = %s,
                    working_days = %s, description = %s, latitude = %s, longitude = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = (
                center_name.strip(), address.strip(), district.strip(), city.strip(),
                state.strip() if state else 'Kerala', pincode.strip(), phone.strip(),
                email.strip().lower() if email else None, opening_time.strip(), closing_time.strip(),
                working_days.strip(), description.strip() if description else None,
                float(latitude) if latitude is not None and latitude != '' else None,
                float(longitude) if longitude is not None and longitude != '' else None,
                center_id
            )

        execute_db(sql, params)
        return True

    @staticmethod
    def delete(center_id, ngo_id=None):
        """
        Deletes a donation center.
        If ngo_id is provided, strictly enforces ownership (security isolation).
        Returns True if deleted, False if permission denied or not found.
        """
        if ngo_id is not None:
            center = DonationCenter.get_by_id(center_id)
            if not center or center['ngo_id'] != ngo_id:
                return False

        sql = "DELETE FROM donation_centers WHERE id = %s"
        execute_db(sql, (center_id,))
        return True

    @staticmethod
    def update_status(center_id, status):
        """Admin helper to update center approval or operational status."""
        sql = "UPDATE donation_centers SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        return execute_db(sql, (status, center_id))

    @staticmethod
    def get_counts(ngo_id=None):
        """
        Calculates center counts grouped by status.
        If ngo_id is provided, calculates specifically for that NGO.
        """
        if ngo_id:
            sql = """
                SELECT status, COUNT(*) as count
                FROM donation_centers
                WHERE ngo_id = %s
                GROUP BY status
            """
            rows = query_db(sql, (ngo_id,))
        else:
            sql = """
                SELECT status, COUNT(*) as count
                FROM donation_centers
                GROUP BY status
            """
            rows = query_db(sql)

        counts = {
            'total': 0,
            'active': 0,
            'inactive': 0,
            'pending': 0,
            'rejected': 0,
            'approved': 0
        }
        for r in rows:
            st = (r['status'] or '').lower()
            cnt = r['count']
            counts['total'] += cnt
            if st in counts:
                counts[st] = cnt
            else:
                counts[st] = cnt
        return counts

    @staticmethod
    def get_distinct_districts():
        """Retrieve sorted list of all unique districts with active donation centers."""
        sql = """
            SELECT DISTINCT district 
            FROM donation_centers 
            WHERE status IN ('Active', 'Approved') 
            ORDER BY district ASC
        """
        rows = query_db(sql)
        return [r['district'] for r in rows if r.get('district')]
