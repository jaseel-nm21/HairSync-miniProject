"""
Inventory Models (Module 4)
Handles Hair Inventory (collected donor hair bundles) and Wig Inventory
(natural-hair and medical cranial prostheses) for NGOs.
"""

from database.db import query_db, execute_db


class HairInventory:
    VALID_STATUSES = ['In Stock', 'In Processing', 'Used in Wig', 'Disposed']

    @classmethod
    def create(cls, ngo_id, hair_type, hair_length, hair_condition,
               quantity_or_weight=None, status='In Stock', notes=None, donation_id=None):
        """Add collected hair batch to NGO inventory."""
        if status not in cls.VALID_STATUSES:
            status = 'In Stock'

        sql = """
            INSERT INTO hair_inventory
            (ngo_id, donation_id, hair_type, hair_length, hair_condition, quantity_or_weight, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            ngo_id,
            donation_id if donation_id else None,
            str(hair_type).strip(),
            float(hair_length),
            str(hair_condition).strip(),
            str(quantity_or_weight).strip() if quantity_or_weight else None,
            status,
            str(notes).strip() if notes else None
        ))
        return res['lastrowid']

    @staticmethod
    def get_by_id(item_id):
        """Fetch a specific hair inventory item."""
        sql = """
            SELECT hi.*, np.organization_name as ngo_name
            FROM hair_inventory hi
            JOIN ngo_profiles np ON hi.ngo_id = np.id
            WHERE hi.id = %s
        """
        return query_db(sql, (item_id,), one=True)

    @staticmethod
    def get_by_ngo(ngo_id, status=None, hair_type=None):
        """Fetch all hair inventory items for an NGO with optional filters."""
        sql = """
            SELECT hi.*, d.donation_date, u.name as donor_name
            FROM hair_inventory hi
            LEFT JOIN donations d ON hi.donation_id = d.id
            LEFT JOIN donor_profiles dp ON d.donor_id = dp.id
            LEFT JOIN users u ON dp.user_id = u.id
            WHERE hi.ngo_id = %s
        """
        params = [ngo_id]
        if status:
            sql += " AND hi.status = %s"
            params.append(status)
        if hair_type:
            sql += " AND hi.hair_type = %s"
            params.append(hair_type)

        sql += " ORDER BY hi.created_at DESC"
        return query_db(sql, tuple(params))

    @classmethod
    def update_status(cls, item_id, new_status, notes=None):
        """Update inventory status (e.g., In Stock -> Used in Wig)."""
        if new_status not in cls.VALID_STATUSES:
            return False

        if notes:
            sql = "UPDATE hair_inventory SET status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            execute_db(sql, (new_status, notes, item_id))
        else:
            sql = "UPDATE hair_inventory SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            execute_db(sql, (new_status, item_id))
        return True

    @staticmethod
    def delete(item_id, ngo_id):
        """Delete hair inventory item with NGO ownership check."""
        sql = "DELETE FROM hair_inventory WHERE id = %s AND ngo_id = %s"
        res = execute_db(sql, (item_id, ngo_id))
        return res['rowcount'] > 0

    @staticmethod
    def count_by_ngo(ngo_id):
        """Return stock metrics for an NGO."""
        sql = """
            SELECT 
                COUNT(*) as total_items,
                SUM(CASE WHEN status = 'In Stock' THEN 1 ELSE 0 END) as in_stock,
                SUM(CASE WHEN status = 'In Processing' THEN 1 ELSE 0 END) as in_processing,
                SUM(CASE WHEN status = 'Used in Wig' THEN 1 ELSE 0 END) as used_in_wig
            FROM hair_inventory
            WHERE ngo_id = %s
        """
        row = query_db(sql, (ngo_id,), one=True)
        return {
            'total_items': row['total_items'] or 0,
            'in_stock': row['in_stock'] or 0,
            'in_processing': row['in_processing'] or 0,
            'used_in_wig': row['used_in_wig'] or 0
        } if row else {'total_items': 0, 'in_stock': 0, 'in_processing': 0, 'used_in_wig': 0}

    @classmethod
    def auto_add_from_donation(cls, donation_id):
        """Automatically create a hair inventory entry from a completed donation if not already present."""
        existing = query_db("SELECT id FROM hair_inventory WHERE donation_id = %s", (donation_id,), one=True)
        if existing:
            return existing['id']

        don = query_db("SELECT * FROM donations WHERE id = %s", (donation_id,), one=True)
        if not don:
            return None

        return cls.create(
            ngo_id=don['ngo_id'],
            hair_type=don['hair_type'],
            hair_length=don['hair_length'],
            hair_condition=don['hair_condition'],
            quantity_or_weight=don.get('quantity_or_estimated_weight'),
            status='In Stock',
            notes=f"Auto-cataloged from donation #{don['id']}.",
            donation_id=don['id']
        )


class Wig:
    VALID_STATUSES = ['Available', 'Assigned', 'In Preparation', 'Dispatched', 'Delivered']
    VALID_SIZES = ['Small', 'Medium', 'Large', 'Adjustable']
    VALID_SOURCES = ['Natural', 'Synthetic', 'Blend']

    @classmethod
    def create(cls, ngo_id, wig_type, hair_color, hair_length,
               size='Medium', hair_source='Natural', condition='New / Sanitized',
               status='Available', notes=None):
        """Add crafted wig to NGO inventory."""
        if status not in cls.VALID_STATUSES:
            status = 'Available'
        if size not in cls.VALID_SIZES:
            size = 'Medium'
        if hair_source not in cls.VALID_SOURCES:
            hair_source = 'Natural'

        sql = """
            INSERT INTO wigs
            (ngo_id, wig_type, hair_source, hair_color, hair_length, size, condition, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            ngo_id,
            str(wig_type).strip(),
            hair_source,
            str(hair_color).strip(),
            float(hair_length),
            size,
            str(condition).strip(),
            status,
            str(notes).strip() if notes else None
        ))
        return res['lastrowid']

    @staticmethod
    def get_by_id(wig_id):
        """Fetch full wig details."""
        sql = """
            SELECT w.*, np.organization_name as ngo_name
            FROM wigs w
            JOIN ngo_profiles np ON w.ngo_id = np.id
            WHERE w.id = %s
        """
        return query_db(sql, (wig_id,), one=True)

    @staticmethod
    def get_by_ngo(ngo_id, status=None, hair_source=None):
        """Fetch wigs belonging to an NGO with optional status/source filter."""
        sql = "SELECT * FROM wigs WHERE ngo_id = %s"
        params = [ngo_id]
        if status:
            sql += " AND status = %s"
            params.append(status)
        if hair_source:
            sql += " AND hair_source = %s"
            params.append(hair_source)

        sql += " ORDER BY created_at DESC"
        return query_db(sql, tuple(params))

    @staticmethod
    def get_available_for_ngo(ngo_id):
        """Fetch all wigs available for assignment in this NGO."""
        sql = """
            SELECT * FROM wigs
            WHERE ngo_id = %s AND status = 'Available'
            ORDER BY wig_type ASC, hair_length ASC
        """
        return query_db(sql, (ngo_id,))

    @classmethod
    def update(cls, wig_id, ngo_id, wig_type, hair_color, hair_length,
               size='Medium', hair_source='Natural', condition='New / Sanitized',
               status='Available', notes=None):
        """Update wig details with NGO ownership verification."""
        if status not in cls.VALID_STATUSES:
            status = 'Available'
        if size not in cls.VALID_SIZES:
            size = 'Medium'
        if hair_source not in cls.VALID_SOURCES:
            hair_source = 'Natural'

        sql = """
            UPDATE wigs
            SET wig_type = %s, hair_source = %s, hair_color = %s, hair_length = %s,
                size = %s, condition = %s, status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND ngo_id = %s
        """
        res = execute_db(sql, (
            str(wig_type).strip(),
            hair_source,
            str(hair_color).strip(),
            float(hair_length),
            size,
            str(condition).strip(),
            status,
            str(notes).strip() if notes else None,
            wig_id,
            ngo_id
        ))
        return res['rowcount'] > 0

    @classmethod
    def update_status(cls, wig_id, new_status):
        """Update wig status (e.g. Available -> Assigned -> Dispatched -> Delivered)."""
        if new_status not in cls.VALID_STATUSES:
            return False
        sql = "UPDATE wigs SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        execute_db(sql, (new_status, wig_id))
        return True

    @staticmethod
    def delete(wig_id, ngo_id):
        """Delete wig record if not assigned."""
        assigned = query_db("SELECT id FROM wig_requests WHERE assigned_wig_id = %s", (wig_id,), one=True)
        if assigned:
            return False, "Cannot delete a wig that is currently assigned to a recipient request."

        sql = "DELETE FROM wigs WHERE id = %s AND ngo_id = %s"
        res = execute_db(sql, (wig_id, ngo_id))
        if res['rowcount'] > 0:
            return True, "Wig record deleted successfully."
        return False, "Wig record not found or access denied."

    @staticmethod
    def count_by_ngo(ngo_id):
        """Count wigs for an NGO by status."""
        sql = """
            SELECT 
                COUNT(*) as total_wigs,
                SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'Assigned' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN status IN ('In Preparation', 'Dispatched', 'Out for Delivery') THEN 1 ELSE 0 END) as in_transit,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered
            FROM wigs
            WHERE ngo_id = %s
        """
        row = query_db(sql, (ngo_id,), one=True)
        return {
            'total_wigs': row['total_wigs'] or 0,
            'available': row['available'] or 0,
            'assigned': row['assigned'] or 0,
            'in_transit': row['in_transit'] or 0,
            'delivered': row['delivered'] or 0
        } if row else {'total_wigs': 0, 'available': 0, 'assigned': 0, 'in_transit': 0, 'delivered': 0}

    @staticmethod
    def count_all():
        """Count system-wide wigs."""
        sql = """
            SELECT 
                COUNT(*) as total_wigs,
                SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered
            FROM wigs
        """
        row = query_db(sql, one=True)
        return {
            'total_wigs': row['total_wigs'] or 0,
            'available': row['available'] or 0,
            'delivered': row['delivered'] or 0
        } if row else {'total_wigs': 0, 'available': 0, 'delivered': 0}
