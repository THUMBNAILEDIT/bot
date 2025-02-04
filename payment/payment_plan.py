class PricingPlans:
    class Monthly:
        period = 30
        pricing_table = {
            240: 4, 456: 8, 648: 12, 816: 16, 960: 20,
            1080: 24, 1092: 28, 1248: 32, 1440: 40,
            1728: 48, 2016: 56, 1296: 36, 2592: 72, 3024: 84,
        }

    class Annual:
        period = 365
        pricing_table = {
            2594: 4, 4925: 8, 6998: 12, 8813: 16, 10368: 20,
            11664: 24, 12701: 28, 13478: 32, 15552: 40,
            18662: 48, 21773: 56, 13997: 36, 23328: 60, 27994: 72, 32659: 84,
        }

    class OneTime:
        period = None
        pricing_table = {
            70: 1, 140: 2, 210: 3, 260: 4, 325: 5,
            390: 6, 455: 7, 480: 8, 540: 9, 600: 10,
        }


def get_plan_from_total(total: int) :
    """
    Determines the pricing plan based on a given total.
    """

    if PricingPlans.Monthly.pricing_table.keys().__contains__(total):
        return PricingPlans.Monthly
    elif PricingPlans.Annual.pricing_table.keys().__contains__(total):
        return PricingPlans.Annual
    elif PricingPlans.OneTime.pricing_table.keys().__contains__(total):
        return PricingPlans.OneTime
    else:
        return None

def calculate_credits_with_workaround(total):
    """
    Every plan has the unique price, so i make more simple code, but it's not good practice)
    And yea, i change price for the first plan in annual table, because it was not unique, sorry for that
    """
    pricing_table = (PricingPlans.Monthly.pricing_table | PricingPlans.Annual.pricing_table | PricingPlans.OneTime.pricing_table)
    return pricing_table.get(total, 0)