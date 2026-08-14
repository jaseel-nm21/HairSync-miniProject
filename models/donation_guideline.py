"""
DonationGuideline Model (Module 3)
Allows NGOs to establish and manage criteria for accepting hair donations,
and dynamically evaluates donor eligibility against specific guidelines.
"""

from database.db import query_db, execute_db


class DonationGuideline:
    DEFAULT_GUIDELINES = {
        'minimum_hair_length': 20.0,
        'allowed_hair_types': 'Straight,Wavy,Curly,Coily',
        'allow_colored_hair': 'Requires Review',
        'allow_chemically_treated': 'Not Allowed',
        'allow_bleached_hair': 'Not Allowed',
        'minimum_condition': 'Clean, dry, tied securely in ponytail or braid at both ends',
        'additional_requirements': 'Hair must be washed within 24 hours prior to donation. Gray hair is accepted.'
    }

    @staticmethod
    def get_by_ngo_id(ngo_id):
        """Fetch donation guidelines for a specific NGO."""
        sql = "SELECT * FROM donation_guidelines WHERE ngo_id = %s"
        return query_db(sql, (ngo_id,), one=True)

    @classmethod
    def get_or_default(cls, ngo_id):
        """Fetch NGO guidelines or return standardized platform defaults if none set."""
        guide = cls.get_by_ngo_id(ngo_id)
        if guide:
            return guide
        default = dict(cls.DEFAULT_GUIDELINES)
        default['ngo_id'] = ngo_id
        default['id'] = None
        return default

    @classmethod
    def upsert(cls, ngo_id, minimum_hair_length, allowed_hair_types,
               allow_colored_hair, allow_chemically_treated, allow_bleached_hair,
               minimum_condition=None, additional_requirements=None):
        """
        Inserts new guidelines or updates existing guidelines for the NGO.
        """
        existing = cls.get_by_ngo_id(ngo_id)
        if existing:
            sql = """
                UPDATE donation_guidelines
                SET minimum_hair_length = %s,
                    allowed_hair_types = %s,
                    allow_colored_hair = %s,
                    allow_chemically_treated = %s,
                    allow_bleached_hair = %s,
                    minimum_condition = %s,
                    additional_requirements = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE ngo_id = %s
            """
            execute_db(sql, (
                float(minimum_hair_length),
                str(allowed_hair_types).strip(),
                str(allow_colored_hair).strip(),
                str(allow_chemically_treated).strip(),
                str(allow_bleached_hair).strip(),
                str(minimum_condition).strip() if minimum_condition else None,
                str(additional_requirements).strip() if additional_requirements else None,
                ngo_id
            ))
            return existing['id']
        else:
            sql = """
                INSERT INTO donation_guidelines
                (ngo_id, minimum_hair_length, allowed_hair_types, allow_colored_hair,
                 allow_chemically_treated, allow_bleached_hair, minimum_condition, additional_requirements)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            res = execute_db(sql, (
                ngo_id,
                float(minimum_hair_length),
                str(allowed_hair_types).strip(),
                str(allow_colored_hair).strip(),
                str(allow_chemically_treated).strip(),
                str(allow_bleached_hair).strip(),
                str(minimum_condition).strip() if minimum_condition else None,
                str(additional_requirements).strip() if additional_requirements else None
            ))
            return res['lastrowid']

    @classmethod
    def evaluate_donor(cls, guideline, hair_length, hair_type, hair_condition,
                       is_colored=False, is_chemically_treated=False, is_bleached=False):
        """
        Evaluates donor details against the provided guideline.
        Returns:
            dict {
                'status': 'Eligible' | 'Requires Review' | 'Not Eligible',
                'eligible': bool,
                'messages': list of strings,
                'details': dict
            }
        """
        if not guideline:
            guideline = cls.DEFAULT_GUIDELINES

        min_len = float(guideline.get('minimum_hair_length', 20.0))
        allowed_types_str = guideline.get('allowed_hair_types', 'Straight,Wavy,Curly,Coily')
        allowed_types = [t.strip().lower() for t in allowed_types_str.split(',') if t.strip()]

        allow_color = guideline.get('allow_colored_hair', 'Requires Review')
        allow_chem = guideline.get('allow_chemically_treated', 'Not Allowed')
        allow_bleach = guideline.get('allow_bleached_hair', 'Not Allowed')

        status = 'Eligible'
        messages = []
        details = {}

        # 1. Hair Length Check
        try:
            length_val = float(hair_length)
        except (ValueError, TypeError):
            length_val = 0.0

        if length_val < min_len:
            status = 'Not Eligible'
            messages.append(f"Hair length ({length_val:.1f} cm) is below the required minimum of {min_len:.1f} cm.")
            details['length'] = 'Failed'
        else:
            details['length'] = 'Passed'

        # 2. Hair Type Check
        if hair_type and hair_type.strip().lower() not in allowed_types:
            # If not in allowed list
            if status != 'Not Eligible':
                status = 'Requires Review'
            messages.append(f"Hair type '{hair_type}' may require special processing.")
            details['type'] = 'Requires Review'
        else:
            details['type'] = 'Passed'

        # 3. Bleached Hair Check
        if is_bleached:
            if allow_bleach == 'Not Allowed':
                status = 'Not Eligible'
                messages.append("Bleached or heavily lightened hair is not accepted by this organization.")
                details['bleached'] = 'Failed'
            elif allow_bleach == 'Requires Review':
                if status != 'Not Eligible':
                    status = 'Requires Review'
                messages.append("Bleached hair requires in-person manual evaluation.")
                details['bleached'] = 'Requires Review'
            else:
                details['bleached'] = 'Passed'
        else:
            details['bleached'] = 'Passed'

        # 4. Chemically Treated Check (perm, rebonding, relaxer)
        if is_chemically_treated:
            if allow_chem == 'Not Allowed':
                status = 'Not Eligible'
                messages.append("Chemically treated / relaxed / permed hair is not accepted.")
                details['chemically_treated'] = 'Failed'
            elif allow_chem == 'Requires Review':
                if status != 'Not Eligible':
                    status = 'Requires Review'
                messages.append("Chemically treated hair requires assessment by center technicians.")
                details['chemically_treated'] = 'Requires Review'
            else:
                details['chemically_treated'] = 'Passed'
        else:
            details['chemically_treated'] = 'Passed'

        # 5. Colored Hair Check
        if is_colored:
            if allow_color == 'Not Allowed':
                status = 'Not Eligible'
                messages.append("Artificially colored / dyed hair is not accepted.")
                details['colored'] = 'Failed'
            elif allow_color == 'Requires Review':
                if status != 'Not Eligible':
                    status = 'Requires Review'
                messages.append("Colored hair requires review (temporary vs permanent dye check).")
                details['colored'] = 'Requires Review'
            else:
                details['colored'] = 'Passed'
        else:
            details['colored'] = 'Passed'

        if not messages:
            messages.append("Congratulations! Your hair meets all guidelines for donation.")

        return {
            'status': status,
            'eligible': status in ('Eligible', 'Requires Review'),
            'messages': messages,
            'details': details
        }
