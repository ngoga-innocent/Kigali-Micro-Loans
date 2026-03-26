from datetime import timedelta

def calculate_due_date(start_date, value, unit):
    if unit == "days":
        return start_date + timedelta(days=value)
    elif unit == "weeks":
        return start_date + timedelta(weeks=value)
    elif unit == "months":
        return start_date + timedelta(days=value * 30)
def get_installments(period_value, period_unit, frequency):

    if period_unit == "days":
        total_days = period_value
    elif period_unit == "weeks":
        total_days = period_value * 7
    elif period_unit == "months":
        total_days = period_value * 30

    if frequency == "daily":
        return total_days

    elif frequency == "weekly":
        return total_days // 7

    elif frequency == "monthly":
        return total_days // 30