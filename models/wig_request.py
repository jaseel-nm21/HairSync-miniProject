"""
Wig Request Model (Modules 5 & 6)
Handles recipient natural-hair wig requests, medical reasons, delivery specifications,
NGO review & wig assignment, and status-based tracking timeline logs.
"""

from database.db import query_db, execute_db
from models.inventory import Wig


class WigRequest:
    VALID_STATUSES = [
        'Submitted',
        'Under Review',
        'Approved',
        'Rejected',
        'Wig Assigned',
        'Preparing',
        'Ready for Dispatch',
        'Dispatched',
        'In Transit',
        'Out for Delivery',
        'Delivered'
    ]

    # Logical sequence of progression for tracking display
    STATUS_SEQUENCE = [
        'Submitted',
        'Under Review',
        'Approved',
        'Wig Assigned',
        'Preparing',
        'Ready for Dispatch',
        'Dispatched',
        'In Transit',
        'Out for Delivery',
        'Delivered'
    ]

    @classmethod
    def create(cls, recipient_id, preferred_wig_type, preferred_length, preferred_color,
               preferred_size, reason_for_request, delivery_address, delivery_city,
               delivery_district, delivery_pincode, contact_phone, additional_notes=None,
               ngo_id=None, hair_source='Natural', user_id=None):
        """Creates a new wig request and logs initial tracking status."""
        sql = """
            INSERT INTO wig_requests
            (recipient_id, ngo_id, preferred_wig_type, hair_source, preferred_length,
             preferred_color, preferred_size, reason_for_request, delivery_address,
             delivery_city, delivery_district, delivery_pincode, contact_phone,
             additional_notes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Submitted')
        """
        res = execute_db(sql, (
            recipient_id,
            ngo_id if ngo_id else None,
            str(preferred_wig_type).strip(),
            hair_source,
            float(preferred_length),
            str(preferred_color).strip(),
            str(preferred_size).strip(),
            str(reason_for_request).strip(),
            str(delivery_address).strip(),
            str(delivery_city).strip(),
            str(delivery_district).strip(),
            str(delivery_pincode).strip(),
            str(contact_phone).strip(),
            str(additional_notes).strip() if additional_notes else None
        ))
        request_id = res['lastrowid']

        # Log initial tracking entry
        cls.log_tracking(
            request_id=request_id,
            status='Submitted',
            remarks='Natural-hair wig request submitted by recipient.',
            user_id=user_id
        )

        return request_id

    @staticmethod
    def get_by_id(request_id):
        """Fetches full request record joined with recipient, NGO, and wig details."""
        sql = """
            SELECT wr.*,
                   u.name as recipient_name,
                   u.email as recipient_email,
                   rp.date_of_birth,
                   rp.reason_for_wig as profile_reason,
                   np.organization_name as ngo_name,
                   np.phone as ngo_phone,
                   np.email as ngo_email,
                   w.wig_type as assigned_wig_name,
                   w.hair_color as assigned_wig_color,
                   w.hair_length as assigned_wig_length,
                   w.hair_source as assigned_wig_source,
                   w.size as assigned_wig_size,
                   w.condition as assigned_wig_condition
            FROM wig_requests wr
            JOIN recipient_profiles rp ON wr.recipient_id = rp.id
            JOIN users u ON rp.user_id = u.id
            LEFT JOIN ngo_profiles np ON wr.ngo_id = np.id
            LEFT JOIN wigs w ON wr.assigned_wig_id = w.id
            WHERE wr.id = %s
        """
        return query_db(sql, (request_id,), one=True)

    @staticmethod
    def get_by_recipient(recipient_id):
        """Fetches all requests for a specific recipient."""
        sql = """
            SELECT wr.*,
                   np.organization_name as ngo_name,
                   w.wig_type as assigned_wig_name
            FROM wig_requests wr
            LEFT JOIN ngo_profiles np ON wr.ngo_id = np.id
            LEFT JOIN wigs w ON wr.assigned_wig_id = w.id
            WHERE wr.recipient_id = %s
            ORDER BY wr.created_at DESC
        """
        return query_db(sql, (recipient_id,))

    @staticmethod
    def get_by_ngo(ngo_id, status=None):
        """
        Fetches requests for an NGO: requests assigned to this NGO,
        plus open 'Submitted' unassigned requests so NGO can review and claim them.
        """
        sql = """
            SELECT wr.*,
                   u.name as recipient_name,
                   u.email as recipient_email,
                   rp.phone as recipient_phone,
                   rp.district as recipient_district,
                   w.wig_type as assigned_wig_name
            FROM wig_requests wr
            JOIN recipient_profiles rp ON wr.recipient_id = rp.id
            JOIN users u ON rp.user_id = u.id
            LEFT JOIN wigs w ON wr.assigned_wig_id = w.id
            WHERE (wr.ngo_id = %s OR (wr.ngo_id IS NULL AND wr.status = 'Submitted'))
        """
        params = [ngo_id]
        if status:
            sql += " AND wr.status = %s"
            params.append(status)

        sql += " ORDER BY wr.created_at DESC"
        return query_db(sql, tuple(params))

    @staticmethod
    def get_all(status=None, district=None, ngo_id=None):
        """Platform-wide wig requests list for admin oversight."""
        sql = """
            SELECT wr.*,
                   u.name as recipient_name,
                   u.email as recipient_email,
                   np.organization_name as ngo_name,
                   w.wig_type as assigned_wig_name
            FROM wig_requests wr
            JOIN recipient_profiles rp ON wr.recipient_id = rp.id
            JOIN users u ON rp.user_id = u.id
            LEFT JOIN ngo_profiles np ON wr.ngo_id = np.id
            LEFT JOIN wigs w ON wr.assigned_wig_id = w.id
            WHERE 1=1
        """
        params = []
        if status:
            sql += " AND wr.status = %s"
            params.append(status)
        if district:
            sql += " AND wr.delivery_district = %s"
            params.append(district)
        if ngo_id:
            sql += " AND wr.ngo_id = %s"
            params.append(ngo_id)

        sql += " ORDER BY wr.created_at DESC"
        return query_db(sql, tuple(params))

    @classmethod
    def update_status(cls, request_id, new_status, remarks=None, user_id=None,
                      rejection_reason=None, tracking_number=None,
                      courier_service=None, estimated_delivery_date=None, ngo_id=None):
        """Updates request status and appends entry to wig_tracking_logs."""
        if new_status not in cls.VALID_STATUSES:
            return False, "Invalid status specified."

        req = cls.get_by_id(request_id)
        if not req:
            return False, "Wig request record not found."

        fields = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
        params = [new_status]

        if ngo_id and not req['ngo_id']:
            fields.append("ngo_id = %s")
            params.append(ngo_id)
        if rejection_reason is not None:
            fields.append("rejection_reason = %s")
            params.append(str(rejection_reason).strip())
        if tracking_number is not None:
            fields.append("tracking_number = %s")
            params.append(str(tracking_number).strip())
        if courier_service is not None:
            fields.append("courier_service = %s")
            params.append(str(courier_service).strip())
        if estimated_delivery_date is not None:
            fields.append("estimated_delivery_date = %s")
            params.append(str(estimated_delivery_date).strip())

        params.append(request_id)
        sql = f"UPDATE wig_requests SET {', '.join(fields)} WHERE id = %s"
        execute_db(sql, tuple(params))

        # Sync assigned wig status if applicable
        if req['assigned_wig_id']:
            if new_status in ['In Preparation', 'Dispatched', 'Delivered']:
                Wig.update_status(req['assigned_wig_id'], new_status)
            elif new_status == 'Rejected':
                # Return wig to Available
                Wig.update_status(req['assigned_wig_id'], 'Available')
                execute_db("UPDATE wig_requests SET assigned_wig_id = NULL WHERE id = %s", (request_id,))

        # Log tracking entry
        cls.log_tracking(
            request_id=request_id,
            status=new_status,
            remarks=remarks if remarks else f"Status advanced to {new_status}.",
            user_id=user_id
        )

        return True, f"Request #{request_id} updated to {new_status}."

    @classmethod
    def assign_wig(cls, request_id, wig_id, ngo_id, remarks=None, user_id=None):
        """Assigns an available wig from the NGO inventory to an approved request."""
        req = cls.get_by_id(request_id)
        if not req:
            return False, "Wig request not found."

        wig = Wig.get_by_id(wig_id)
        if not wig or wig['ngo_id'] != ngo_id:
            return False, "Selected wig not found or does not belong to your organization."
        if wig['status'] != 'Available':
            return False, f"Selected wig is not available (current status: {wig['status']})."

        # Update wig status to 'Assigned'
        Wig.update_status(wig_id, 'Assigned')

        # Update request
        sql = """
            UPDATE wig_requests
            SET assigned_wig_id = %s, ngo_id = %s, status = 'Wig Assigned', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        execute_db(sql, (wig_id, ngo_id, request_id))

        # Log tracking entry
        assign_remarks = remarks if remarks else f"Matched and assigned wig: {wig['wig_type']} ({wig['hair_color']}, {wig['hair_length']} cm)."
        cls.log_tracking(
            request_id=request_id,
            status='Wig Assigned',
            remarks=assign_remarks,
            user_id=user_id
        )

        return True, f"Wig #{wig_id} successfully assigned to request #{request_id}."

    @staticmethod
    def log_tracking(request_id, status, remarks=None, user_id=None):
        """Inserts an immutable tracking event in wig_tracking_logs."""
        sql = """
            INSERT INTO wig_tracking_logs (wig_request_id, status, remarks, updated_by_user_id)
            VALUES (%s, %s, %s, %s)
        """
        execute_db(sql, (
            request_id,
            status,
            remarks,
            user_id if user_id else None
        ))

    @staticmethod
    def get_tracking_timeline(request_id):
        """Fetches chronological tracking logs for display."""
        sql = """
            SELECT wtl.*, u.name as updater_name, u.role as updater_role
            FROM wig_tracking_logs wtl
            LEFT JOIN users u ON wtl.updated_by_user_id = u.id
            WHERE wtl.wig_request_id = %s
            ORDER BY wtl.created_at ASC, wtl.id ASC
        """
        return query_db(sql, (request_id,))

    @staticmethod
    def count_by_recipient(recipient_id):
        """Count recipient requests."""
        sql = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Submitted' THEN 1 ELSE 0 END) as submitted,
                SUM(CASE WHEN status = 'Under Review' THEN 1 ELSE 0 END) as under_review,
                SUM(CASE WHEN status IN ('Approved', 'Wig Assigned', 'Preparing', 'Ready for Dispatch') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status IN ('Dispatched', 'In Transit', 'Out for Delivery') THEN 1 ELSE 0 END) as dispatched,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered
            FROM wig_requests
            WHERE recipient_id = %s
        """
        row = query_db(sql, (recipient_id,), one=True)
        return {
            'total': row['total'] or 0,
            'submitted': row['submitted'] or 0,
            'under_review': row['under_review'] or 0,
            'in_progress': row['in_progress'] or 0,
            'dispatched': row['dispatched'] or 0,
            'delivered': row['delivered'] or 0
        } if row else {'total': 0, 'submitted': 0, 'under_review': 0, 'in_progress': 0, 'dispatched': 0, 'delivered': 0}

    @staticmethod
    def count_by_ngo(ngo_id):
        """Count requests for an NGO."""
        sql = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Under Review' THEN 1 ELSE 0 END) as under_review,
                SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'Wig Assigned' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN status IN ('Preparing', 'Ready for Dispatch') THEN 1 ELSE 0 END) as preparing,
                SUM(CASE WHEN status IN ('Dispatched', 'In Transit', 'Out for Delivery') THEN 1 ELSE 0 END) as dispatched,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered
            FROM wig_requests
            WHERE ngo_id = %s
        """
        row = query_db(sql, (ngo_id,), one=True)
        return {
            'total': row['total'] or 0,
            'under_review': row['under_review'] or 0,
            'approved': row['approved'] or 0,
            'assigned': row['assigned'] or 0,
            'preparing': row['preparing'] or 0,
            'dispatched': row['dispatched'] or 0,
            'delivered': row['delivered'] or 0
        } if row else {'total': 0, 'under_review': 0, 'approved': 0, 'assigned': 0, 'preparing': 0, 'dispatched': 0, 'delivered': 0}

    @staticmethod
    def count_all():
        """Count platform-wide requests for Admin."""
        sql = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Submitted' THEN 1 ELSE 0 END) as submitted,
                SUM(CASE WHEN status = 'Under Review' THEN 1 ELSE 0 END) as under_review,
                SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'Wig Assigned' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN status IN ('Preparing', 'Ready for Dispatch') THEN 1 ELSE 0 END) as preparing,
                SUM(CASE WHEN status IN ('Dispatched', 'In Transit', 'Out for Delivery') THEN 1 ELSE 0 END) as dispatched,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected
            FROM wig_requests
        """
        row = query_db(sql, one=True)
        return {
            'total': row['total'] or 0,
            'submitted': row['submitted'] or 0,
            'under_review': row['under_review'] or 0,
            'approved': row['approved'] or 0,
            'assigned': row['assigned'] or 0,
            'preparing': row['preparing'] or 0,
            'dispatched': row['dispatched'] or 0,
            'delivered': row['delivered'] or 0,
            'rejected': row['rejected'] or 0
        } if row else {
            'total': 0, 'submitted': 0, 'under_review': 0, 'approved': 0,
            'assigned': 0, 'preparing': 0, 'dispatched': 0, 'delivered': 0, 'rejected': 0
        }
