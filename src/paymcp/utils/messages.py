def payment_prompt_message(url, amount, currency):
    return (
        f"Please follow the link below to pay:\n\n{url}\n\n"
        f"Amount: {amount} {currency}.\n"
        "After payment, return here and confirm to continue."
    )

def description_with_price(description:str, price_info:dict):
    extra_desc = (
        f"\nThis is a paid function: {price_info['price']} {price_info['currency']}."
                        " Payment will be requested during execution."
        )
    return description.strip() + extra_desc