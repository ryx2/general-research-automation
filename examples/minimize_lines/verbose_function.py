"""Data processing utilities — deliberately verbose implementation."""

import statistics


def process_sales_data(raw_data):
    """Process raw sales data and return a summary report.

    Takes a list of dicts with keys: product, quantity, price, region.
    Returns a dict with total revenue, average order value, regional breakdowns,
    top products, and basic statistics.
    """
    # Validate that we received data
    if raw_data is None:
        raise ValueError("raw_data cannot be None")

    # Check if the data list is empty
    if len(raw_data) == 0:
        return {
            "total_revenue": 0,
            "total_orders": 0,
            "average_order_value": 0,
            "regions": {},
            "top_products": [],
            "statistics": {},
        }

    # Initialize the total revenue accumulator
    total_revenue = 0

    # Initialize a list to store individual order values
    order_values = []

    # Initialize a dictionary to store revenue by region
    revenue_by_region = {}

    # Initialize a dictionary to store order count by region
    orders_by_region = {}

    # Initialize a dictionary to store revenue by product
    revenue_by_product = {}

    # Initialize a dictionary to store quantity by product
    quantity_by_product = {}

    # Iterate through each record in the raw data
    for record in raw_data:
        # Extract the product name from the current record
        product_name = record["product"]

        # Extract the quantity from the current record
        quantity = record["quantity"]

        # Extract the price from the current record
        price = record["price"]

        # Extract the region from the current record
        region = record["region"]

        # Calculate the order value by multiplying quantity and price
        order_value = quantity * price

        # Add the order value to the total revenue
        total_revenue = total_revenue + order_value

        # Append the order value to the list of order values
        order_values.append(order_value)

        # Check if the region already exists in the revenue dictionary
        if region in revenue_by_region:
            # If it exists, add the order value to the existing total
            revenue_by_region[region] = revenue_by_region[region] + order_value
        else:
            # If it doesn't exist, initialize with the current order value
            revenue_by_region[region] = order_value

        # Check if the region already exists in the orders dictionary
        if region in orders_by_region:
            # If it exists, increment the order count
            orders_by_region[region] = orders_by_region[region] + 1
        else:
            # If it doesn't exist, initialize with 1
            orders_by_region[region] = 1

        # Check if the product already exists in the revenue dictionary
        if product_name in revenue_by_product:
            # If it exists, add the order value to the existing total
            revenue_by_product[product_name] = revenue_by_product[product_name] + order_value
        else:
            # If it doesn't exist, initialize with the current order value
            revenue_by_product[product_name] = order_value

        # Check if the product already exists in the quantity dictionary
        if product_name in quantity_by_product:
            # If it exists, add the quantity to the existing total
            quantity_by_product[product_name] = quantity_by_product[product_name] + quantity
        else:
            # If it doesn't exist, initialize with the current quantity
            quantity_by_product[product_name] = quantity

    # Calculate the total number of orders
    total_orders = len(raw_data)

    # Calculate the average order value
    if total_orders > 0:
        average_order_value = total_revenue / total_orders
    else:
        average_order_value = 0

    # Build the regional breakdown
    regional_breakdown = {}

    # Iterate through each region to build the breakdown
    for region_name in revenue_by_region:
        # Get the revenue for this region
        region_revenue = revenue_by_region[region_name]

        # Get the order count for this region
        region_orders = orders_by_region[region_name]

        # Calculate the average order value for this region
        region_average = region_revenue / region_orders

        # Calculate the percentage of total revenue for this region
        region_percentage = (region_revenue / total_revenue) * 100

        # Create the region summary dictionary
        region_summary = {
            "revenue": region_revenue,
            "orders": region_orders,
            "average_order_value": round(region_average, 2),
            "percentage_of_total": round(region_percentage, 2),
        }

        # Add the region summary to the regional breakdown
        regional_breakdown[region_name] = region_summary

    # Sort products by revenue to find top products
    # First, create a list of tuples (product, revenue, quantity)
    product_revenue_list = []
    for product_name in revenue_by_product:
        product_revenue = revenue_by_product[product_name]
        product_quantity = quantity_by_product[product_name]
        product_tuple = (product_name, product_revenue, product_quantity)
        product_revenue_list.append(product_tuple)

    # Sort the list by revenue in descending order
    sorted_products = sorted(
        product_revenue_list,
        key=lambda x: x[1],
        reverse=True,
    )

    # Take the top 5 products (or fewer if less than 5 exist)
    if len(sorted_products) >= 5:
        top_products_list = sorted_products[:5]
    else:
        top_products_list = sorted_products

    # Convert the top products to a list of dictionaries
    top_products = []
    for product_info in top_products_list:
        product_dict = {
            "product": product_info[0],
            "revenue": product_info[1],
            "quantity": product_info[2],
        }
        top_products.append(product_dict)

    # Calculate statistics on order values
    if len(order_values) > 0:
        # Calculate the minimum order value
        min_order = min(order_values)

        # Calculate the maximum order value
        max_order = max(order_values)

        # Calculate the median order value
        median_order = statistics.median(order_values)

        # Calculate the standard deviation if more than 1 order
        if len(order_values) > 1:
            std_dev = statistics.stdev(order_values)
        else:
            std_dev = 0

        # Build the statistics dictionary
        order_stats = {
            "min": round(min_order, 2),
            "max": round(max_order, 2),
            "median": round(median_order, 2),
            "std_dev": round(std_dev, 2),
        }
    else:
        order_stats = {
            "min": 0,
            "max": 0,
            "median": 0,
            "std_dev": 0,
        }

    # Build the final report dictionary
    report = {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "average_order_value": round(average_order_value, 2),
        "regions": regional_breakdown,
        "top_products": top_products,
        "statistics": order_stats,
    }

    # Return the completed report
    return report
