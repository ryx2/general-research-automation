"""Test verbose_function.py and report line count as the metric."""

import sys
from verbose_function import process_sales_data

TEST_DATA = [
    {"product": "Widget A", "quantity": 10, "price": 25.00, "region": "North"},
    {"product": "Widget B", "quantity": 5, "price": 50.00, "region": "South"},
    {"product": "Widget A", "quantity": 3, "price": 25.00, "region": "South"},
    {"product": "Gadget C", "quantity": 8, "price": 30.00, "region": "North"},
    {"product": "Widget B", "quantity": 2, "price": 50.00, "region": "East"},
    {"product": "Gadget C", "quantity": 15, "price": 30.00, "region": "West"},
    {"product": "Widget A", "quantity": 7, "price": 25.00, "region": "East"},
    {"product": "Doohickey", "quantity": 1, "price": 200.00, "region": "North"},
]


def run_tests():
    """Verify all functionality is preserved."""
    errors = []

    result = process_sales_data(TEST_DATA)

    # Check total revenue: 250 + 250 + 75 + 240 + 100 + 450 + 175 + 200 = 1740
    expected_revenue = 10 * 25 + 5 * 50 + 3 * 25 + 8 * 30 + 2 * 50 + 15 * 30 + 7 * 25 + 1 * 200
    if abs(result["total_revenue"] - expected_revenue) > 0.01:
        errors.append(f"total_revenue: expected {expected_revenue}, got {result['total_revenue']}")

    # Check total orders
    if result["total_orders"] != 8:
        errors.append(f"total_orders: expected 8, got {result['total_orders']}")

    # Check average order value
    expected_avg = round(expected_revenue / 8, 2)
    if abs(result["average_order_value"] - expected_avg) > 0.01:
        errors.append(f"average_order_value: expected {expected_avg}, got {result['average_order_value']}")

    # Check all regions exist
    for region in ["North", "South", "East", "West"]:
        if region not in result["regions"]:
            errors.append(f"Missing region: {region}")

    # Check North region details
    north = result["regions"].get("North", {})
    expected_north_rev = 10 * 25 + 8 * 30 + 1 * 200  # 250 + 240 + 200 = 690
    if abs(north.get("revenue", 0) - expected_north_rev) > 0.01:
        errors.append(f"North revenue: expected {expected_north_rev}, got {north.get('revenue')}")
    if north.get("orders") != 3:
        errors.append(f"North orders: expected 3, got {north.get('orders')}")

    # Check top products
    if len(result["top_products"]) == 0:
        errors.append("top_products is empty")
    elif len(result["top_products"]) > 1:
        for i in range(len(result["top_products"]) - 1):
            if result["top_products"][i]["revenue"] < result["top_products"][i + 1]["revenue"]:
                errors.append("top_products not sorted by revenue descending")
                break

    # Check statistics keys
    stats = result["statistics"]
    for key in ["min", "max", "median", "std_dev"]:
        if key not in stats:
            errors.append(f"Missing stat: {key}")

    # Test empty data
    empty_result = process_sales_data([])
    if empty_result["total_revenue"] != 0:
        errors.append("Empty data should return 0 revenue")
    if empty_result["total_orders"] != 0:
        errors.append("Empty data should return 0 orders")

    # Test None raises ValueError
    try:
        process_sales_data(None)
        errors.append("None input should raise ValueError")
    except ValueError:
        pass

    return errors


if __name__ == "__main__":
    errors = run_tests()
    if errors:
        print("TESTS FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("All tests passed.")
    with open("verbose_function.py") as f:
        line_count = len(f.readlines())
    print(f"line_count: {line_count}")
