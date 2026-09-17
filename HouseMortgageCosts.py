import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

def calculate_stamp_duty(price):
    """Calculates standard UK Stamp Duty for a primary residence."""
    duty = 0
    if price > 1500000:
        duty += (price - 1500000) * 0.12
        price = 1500000
    if price > 925000:
        duty += (price - 925000) * 0.10
        price = 925000
    if price > 250000:
        duty += (price - 250000) * 0.05
    return duty

def get_max_mortgage(monthly_payment, annual_rate, years):
    """Calculates the max loan principal based on a monthly payment."""
    if annual_rate == 0:
        return monthly_payment * years * 12
        
    monthly_rate = (annual_rate / 100) / 12
    total_months = years * 12
    
    principal = monthly_payment * (1 - (1 + monthly_rate)**-total_months) / monthly_rate
    return principal

def calculate_monthly_payment(principal, annual_rate, years):
    """Calculates the monthly payment for a given principal and interest rate."""
    if annual_rate == 0:
        return principal / (years * 12)
    
    monthly_rate = (annual_rate / 100) / 12
    total_months = years * 12
    
    payment = principal * (monthly_rate / (1 - (1 + monthly_rate)**-total_months))
    return payment

def find_max_property_price(total_budget):
    """Uses binary search to find the max house price accounting for stamp duty."""
    low = 0.0
    high = total_budget
    
    for _ in range(50):
        mid = (low + high) / 2
        total_cost = mid + calculate_stamp_duty(mid)
        
        if total_cost > total_budget:
            high = mid
        else:
            low = mid
            
    return low


# --- Streamlit App Setup ---

st.set_page_config(page_title="Affordability Calculator", layout="centered")

st.title("🏡 Property Affordability Calculator")
st.markdown("Calculate what value of property you can afford based on your house sale split and new mortgage budget.")

# Disclaimer
st.caption("*Disclaimer: This tool is for educational and illustrative purposes only and does not constitute financial advice. Affordability estimates do not guarantee mortgage approval. Always consult an independent financial advisor or mortgage broker.*")

# --- Session State for Dynamic Form Fields ---
if 'cost_items' not in st.session_state:
    st.session_state.cost_items = [
        {"id": 1, "name": "Solicitor's fees", "amount": 1800.0},
        {"id": 2, "name": "Survey", "amount": 500.0},
        {"id": 3, "name": "Searches", "amount": 500.0},
        {"id": 4, "name": "Land Registry", "amount": 400.0},
        {"id": 5, "name": "Moving costs", "amount": 1500.0},
        {"id": 6, "name": "Furniture & improvements", "amount": 8000.0}
    ]
    st.session_state.next_id = 7

def add_cost():
    """Appends a new empty cost field to the session state."""
    st.session_state.cost_items.append({"id": st.session_state.next_id, "name": "New Cost", "amount": 0.0})
    st.session_state.next_id += 1

def delete_cost(item_id):
    """Removes a cost field based on its unique ID."""
    st.session_state.cost_items = [item for item in st.session_state.cost_items if item["id"] != item_id]


# --- Sidebar Inputs ---

st.sidebar.header("1. Sale of Current House")
sale_price = st.sidebar.number_input("House sale value (£)", value=850000, step=10000)
mortgage_left = st.sidebar.number_input("Outstanding mortgage (£)", value=220000, step=5000)
early_repayment_penalty = st.sidebar.number_input("Early repayment penalty (£)", value=0.0, step=100.0)

ea_fee_type = st.sidebar.radio("Estate Agent Fee Type", ["Fixed Cost", "Percentage + VAT"])

if ea_fee_type == "Percentage + VAT":
    ea_pct = st.sidebar.number_input("Estate Agent Fee (%)", value=1.0, step=0.1)
    estate_agent = sale_price * (ea_pct / 100) * 1.20 
    st.sidebar.caption(f"**Calculated Fee (inc 20% VAT):** £{estate_agent:,.2f}")
else:
    estate_agent = st.sidebar.number_input("Estate agent fee (£)", value=10440.0, step=100.0)


st.sidebar.header("2. Costs for New House")

# Create headers for the form fields
col_h1, col_h2, col_h3 = st.sidebar.columns([5, 4, 2])
col_h1.caption("**Cost Name**")
col_h2.caption("**Amount (£)**")

fixed_buying_costs = 0.0

# Render dynamic form fields
for i, item in enumerate(st.session_state.cost_items):
    col1, col2, col3 = st.sidebar.columns([5, 4, 2])
    
    new_name = col1.text_input(
        "Name", 
        value=item["name"], 
        key=f"name_{item['id']}", 
        label_visibility="collapsed"
    )
    
    new_amount = col2.number_input(
        "Amount", 
        value=float(item["amount"]), 
        step=100.0, 
        key=f"amount_{item['id']}", 
        label_visibility="collapsed"
    )
    
    st.session_state.cost_items[i]["name"] = new_name
    st.session_state.cost_items[i]["amount"] = new_amount
    fixed_buying_costs += new_amount
    
    if col3.button("❌", key=f"del_{item['id']}", help="Delete this cost"):
        delete_cost(item["id"])
        st.rerun()

st.sidebar.button("+ Add New Cost", on_click=add_cost)

# --- Mid-point Calculations for Available Cash ---
total_profit = sale_price - mortgage_left - early_repayment_penalty - estate_agent
your_share = total_profit / 2
available_cash_for_deposit = your_share - fixed_buying_costs


st.sidebar.markdown("---")
st.sidebar.header("3. New Mortgage Details")

# --- Deposit State Management ---
if 'deposit_overridden' not in st.session_state:
    st.session_state.deposit_overridden = False
if 'prev_available_cash' not in st.session_state:
    st.session_state.prev_available_cash = available_cash_for_deposit

# If upstream sale values changed, force reset the deposit override
if st.session_state.prev_available_cash != available_cash_for_deposit:
    st.session_state.deposit_overridden = False
    st.session_state.user_deposit = float(available_cash_for_deposit)
    st.session_state.prev_available_cash = available_cash_for_deposit

# If user hasn't manually changed the deposit, keep it synced with available cash
if not st.session_state.deposit_overridden:
    st.session_state.user_deposit = float(available_cash_for_deposit)

def reset_deposit():
    st.session_state.deposit_overridden = False
    st.session_state.user_deposit = float(available_cash_for_deposit)

def deposit_changed():
    st.session_state.deposit_overridden = True

col_dep_lbl, col_dep_btn = st.sidebar.columns([3, 2])
with col_dep_lbl:
    st.markdown("**Deposit (£)**")
with col_dep_btn:
    if st.session_state.deposit_overridden:
        st.button("🔄 Reset", on_click=reset_deposit, help="Reset to Cash Available for Deposit")

actual_deposit = st.sidebar.number_input(
    "Deposit (£)", 
    value=st.session_state.get('user_deposit', float(available_cash_for_deposit)), 
    step=1000.0,
    key="user_deposit",
    on_change=deposit_changed,
    label_visibility="collapsed"
)

target_monthly_payment = st.sidebar.number_input("What monthly payment can you afford? (£)", value=1000, step=100)
mortgage_years = st.sidebar.number_input("Length of mortgage (years)", value=14, step=1)
interest_rate = st.sidebar.number_input("Interest rate (%)", value=4.8, step=0.1)


# --- Final Calculations ---
max_mortgage = get_max_mortgage(target_monthly_payment, interest_rate, mortgage_years)
total_buying_power = actual_deposit + max_mortgage
max_property_price = find_max_property_price(total_buying_power)
estimated_stamp_duty = calculate_stamp_duty(max_property_price)


# --- Display Results ---
st.header("Results")

st.subheader("💰 Your Cash from Sale")
col1, col2, col3 = st.columns(3)
col1.metric("Total Profit", f"£{total_profit:,.2f}")
col2.metric("Your Share (50%)", f"£{your_share:,.2f}")
col3.metric("Cash Available for Deposit", f"£{available_cash_for_deposit:,.2f}", help="Your share minus your defined new house fees")

st.subheader("🏦 Your New Mortgage")
col4, col5, col6 = st.columns(3)
col4.metric("Deposit", f"£{actual_deposit:,.2f}")
col5.metric("Target Monthly Payment", f"£{target_monthly_payment:,.2f}")
col6.metric("Max Mortgage Loan", f"£{max_mortgage:,.2f}")

st.markdown("---")
st.subheader("🏠 What can you afford?")

st.success(f"### Maximum Property Value: £{max_property_price:,.2f}")

st.markdown(f"""
**How the budget breaks down:**
* **Property Price:** £{max_property_price:,.2f}
* **Stamp Duty (Estimated):** £{estimated_stamp_duty:,.2f}
* **Total Spent (Price + Duty):** £{(max_property_price + estimated_stamp_duty):,.2f} 
*(Matches Deposit £{actual_deposit:,.0f} + Mortgage £{max_mortgage:,.0f})*
""")


# --- Interest Rate Stress Test Chart ---

st.markdown("---")
st.subheader("📈 Interest Rate Stress Test")
st.markdown(f"If you borrow the full **£{max_mortgage:,.2f}**, here is how your monthly payments will change depending on future interest rates.")

rates_array = np.arange(1.0, 15.5, 0.5)
payments_array = [calculate_monthly_payment(max_mortgage, r, mortgage_years) for r in rates_array]

df_chart = pd.DataFrame({
    "Interest Rate (%)": rates_array,
    "Monthly Payment (£)": payments_array
})

line_chart = alt.Chart(df_chart).mark_line(color='#1f77b4', size=3).encode(
    x=alt.X('Interest Rate (%):Q', scale=alt.Scale(domain=[1, 15])),
    y=alt.Y('Monthly Payment (£):Q', scale=alt.Scale(zero=False)),
    tooltip=[alt.Tooltip('Interest Rate (%):Q', format='.1f'), 
             alt.Tooltip('Monthly Payment (£):Q', format=',.2f')]
)

current_rate_df = pd.DataFrame({
    "Interest Rate (%)": [interest_rate],
    "Monthly Payment (£)": [target_monthly_payment],
    "Label": ["Current Rate"]
})

point_chart = alt.Chart(current_rate_df).mark_point(color='red', size=150, filled=True).encode(
    x='Interest Rate (%):Q',
    y='Monthly Payment (£):Q',
    tooltip=[alt.Tooltip('Interest Rate (%):Q', format='.1f'), 
             alt.Tooltip('Monthly Payment (£):Q', format=',.2f')]
)

text_chart = alt.Chart(current_rate_df).mark_text(
    align='left', baseline='middle', dx=10, dy=-10, color='red', fontSize=12, fontWeight='bold'
).encode(
    x='Interest Rate (%):Q',
    y='Monthly Payment (£):Q',
    text='Label'
)

final_chart = (line_chart + point_chart + text_chart).interactive()
st.altair_chart(final_chart, use_container_width=True)


# --- Zoopla Property Search Integration ---

st.markdown("---")
st.subheader("🔎 See What's Out There")
st.markdown("Ready to start looking? Search Zoopla using your calculated affordability budget.")

# 1. Location Input (Blank by default)
search_location = st.text_input("Enter a location", value="", placeholder="e.g. Nailsea, Bristol, Manchester")

# 2. Radius Dropdown
radius_options = {
    "This area only": 0,
    "+ ¼ mile": 0.25,
    "+ ½ mile": 0.5,
    "+ 1 mile": 1,
    "+ 3 miles": 3,
    "+ 5 miles": 5,
    "+ 10 miles": 10,
    "+ 15 miles": 15,
    "+ 20 miles": 20
}
search_radius = st.selectbox("Radius", options=list(radius_options.keys()))

# 3. Bedrooms Dropdown
beds_options = {
    "Any beds": "",
    "1+": 1,
    "2+": 2,
    "3+": 3,
    "4+": 4,
    "5+": 5
}
search_beds = st.selectbox("Bedrooms", options=list(beds_options.keys()))

# 4. Price Calculation: Round to next highest £25k step
base_price = int(np.ceil(max_property_price / 25000.0) * 25000)
price_plus_25 = base_price + 25000
price_plus_50 = base_price + 50000

price_option_base = f"£{base_price:,.0f} max (Affordability rounded up)"
price_option_25 = f"£{price_plus_25:,.0f} max (+£25k buffer)"
price_option_50 = f"£{price_plus_50:,.0f} max (+£50k buffer)"

price_options = [price_option_base, price_option_25, price_option_50, "No max"]
search_price = st.selectbox("Price", options=price_options, index=0)
st.caption("*(Note: You can easily adjust this price filter later once you see the results on Zoopla)*")

# 5. Property Type Dropdown
prop_type_options = {
    "Show all": "property",
    "Houses": "houses",
    "Flats": "flats",
    "Bungalows": "bungalows",
    "Farms/land": "farms-land"
}
search_type = st.selectbox("Property type", options=list(prop_type_options.keys()))

# --- URL Construction ---
st.write("")
if search_location:
    formatted_location = search_location.lower().strip().replace(" ", "-")
    ptype_path = prop_type_options[search_type]
    
    zoopla_url = f"https://www.zoopla.co.uk/for-sale/{ptype_path}/{formatted_location}/?"
    params = []
    
    if search_price == price_option_base:
        params.append(f"price_max={base_price}")
    elif search_price == price_option_25:
        params.append(f"price_max={price_plus_25}")
    elif search_price == price_option_50:
        params.append(f"price_max={price_plus_50}")
        
    r_val = radius_options[search_radius]
    if r_val > 0:
        params.append(f"radius={r_val}")
    
    b_val = beds_options[search_beds]
    if b_val != "":
        params.append(f"beds_min={b_val}")
        
    if params:
        zoopla_url += "&".join(params)
        
    st.link_button("🏠 Search Zoopla", zoopla_url, type="primary", use_container_width=True)
else:
    st.button("🏠 Search Zoopla", disabled=True, help="Enter a location first", use_container_width=True)