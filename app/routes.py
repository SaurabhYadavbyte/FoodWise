import re
from flask import current_app as app, render_template, request, redirect, url_for, flash
from collections import Counter
from app import db
from app.models import FoodItem, WasteLog, MealPlan, User
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

CATEGORIES = [
    'Vegetables', 'Fruits', 'Dairy', 'Cooked Food', 
    'Bread & Bakery', 'Packaged Food', 'Grains & Pulses', 'Other'
]
UNITS = ['kg', 'g', 'L', 'ml', 'pieces', 'packets']
LOCATIONS = ['Refrigerator', 'Freezer', 'Kitchen Shelf', 'Other']

WASTE_REASONS = [
    'More food was cooked than needed',
    'Too much food was bought',
    'Food expired',
    'Food was forgotten',
    'Meal plans changed',
    'Leftover was not used',
    'Food was stored incorrectly',
    'Food quality became poor',
    'Other'
]

DISPOSAL_METHODS = [
    'Regular Garbage',
    'Wet Waste Bin',
    'Composting',
    'Given to Animals',
    'Other'
]

MEAL_TYPES = ['Breakfast', 'Lunch', 'Dinner', 'Snack']

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    all_foods = FoodItem.query.filter_by(user_id=current_user.id).order_by(FoodItem.expiry_date.asc()).all()
    
    total_items = len(all_foods)
    expired_count = 0
    use_today_count = 0
    use_soon_count = 0
    safe_for_now_count = 0
    
    attention_foods = []
    upcoming_foods = []
    
    for food in all_foods:
        status = food.expiry_status
        if status == 'Expired':
            expired_count += 1
            attention_foods.append(food)
        elif status == 'Use Today':
            use_today_count += 1
            attention_foods.append(food)
        elif status == 'Use Soon':
            use_soon_count += 1
            attention_foods.append(food)
        else:
            safe_for_now_count += 1
            if len(upcoming_foods) < 5:
                upcoming_foods.append(food)
                
    all_wastes = WasteLog.query.filter_by(user_id=current_user.id).all()
    total_waste = len(all_wastes)
    waste_insights = None
    
    if total_waste > 0:
        cat_counts = Counter([w.category for w in all_wastes])
        reason_counts = Counter([w.reason for w in all_wastes])
        disp_counts = Counter([w.disposal_method for w in all_wastes])
        
        waste_insights = {
            'total': total_waste,
            'most_category': cat_counts.most_common(1)[0][0] if cat_counts else "N/A",
            'most_reason': reason_counts.most_common(1)[0][0] if reason_counts else "N/A",
            'most_disposal': disp_counts.most_common(1)[0][0] if disp_counts else "N/A"
        }
                
    return render_template(
        'dashboard.html', 
        total_items=total_items,
        expired_count=expired_count,
        use_today_count=use_today_count,
        use_soon_count=use_soon_count,
        safe_for_now_count=safe_for_now_count,
        attention_foods=attention_foods,
        upcoming_foods=upcoming_foods,
        waste_insights=waste_insights
    )

@app.route('/food')
@login_required
def food_list():
    foods = FoodItem.query.filter_by(user_id=current_user.id).order_by(FoodItem.expiry_date.asc()).all()
    return render_template('food_list.html', foods=foods)

@app.route('/food/add', methods=['GET', 'POST'])
@login_required
def add_food():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category')
        quantity_str = request.form.get('quantity', '')
        unit = request.form.get('unit')
        purchase_date_str = request.form.get('purchase_date')
        expiry_date_str = request.form.get('expiry_date')
        storage_location = request.form.get('storage_location')

        errors = []
        if not name:
            errors.append("Name cannot be empty.")
        if not category:
            errors.append("Category is required.")
        if not unit:
            errors.append("Unit is required.")
        if not storage_location:
            errors.append("Storage location is required.")
        if not expiry_date_str:
            errors.append("Expiry date is required.")
        
        quantity = 0
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
        except ValueError:
            errors.append("Quantity must be a valid number.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('add_food.html', categories=CATEGORIES, units=UNITS, locations=LOCATIONS, form=request.form)

        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()

        food = FoodItem(user_id=current_user.id, 
            name=name,
            category=category,
            quantity=quantity,
            unit=unit,
            purchase_date=purchase_date,
            expiry_date=expiry_date,
            storage_location=storage_location
        )
        db.session.add(food)
        db.session.commit()
        flash('Food added.', 'success')
        return redirect(url_for('food_list'))

    return render_template('add_food.html', categories=CATEGORIES, units=UNITS, locations=LOCATIONS, form={})

@app.route('/food/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_food(id):
    food = FoodItem.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category')
        quantity_str = request.form.get('quantity', '')
        unit = request.form.get('unit')
        purchase_date_str = request.form.get('purchase_date')
        expiry_date_str = request.form.get('expiry_date')
        storage_location = request.form.get('storage_location')

        errors = []
        if not name:
            errors.append("Name cannot be empty.")
        if not category:
            errors.append("Category is required.")
        if not unit:
            errors.append("Unit is required.")
        if not storage_location:
            errors.append("Storage location is required.")
        if not expiry_date_str:
            errors.append("Expiry date is required.")
        
        quantity = 0
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
        except ValueError:
            errors.append("Quantity must be a valid number.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('edit_food.html', food=food, categories=CATEGORIES, units=UNITS, locations=LOCATIONS)

        food.name = name
        food.category = category
        food.quantity = quantity
        food.unit = unit
        food.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        food.expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        food.storage_location = storage_location

        db.session.commit()
        flash('Food updated.', 'success')
        return redirect(url_for('food_list'))

    return render_template('edit_food.html', food=food, categories=CATEGORIES, units=UNITS, locations=LOCATIONS)

@app.route('/food/<int:id>/delete', methods=['POST'])
@login_required
def delete_food(id):
    food = FoodItem.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(food)
    db.session.commit()
    flash('Food removed.', 'success')
    return redirect(url_for('food_list'))

@app.route('/waste')
@login_required
def waste_list():
    wastes = WasteLog.query.filter_by(user_id=current_user.id).order_by(WasteLog.date.desc()).all()
    return render_template('waste_list.html', wastes=wastes)

@app.route('/waste/add', methods=['GET', 'POST'])
@login_required
def add_waste():
    if request.method == 'POST':
        food_name = request.form.get('food_name', '').strip()
        category = request.form.get('category')
        quantity_str = request.form.get('quantity', '')
        unit = request.form.get('unit')
        date_str = request.form.get('date')
        reason = request.form.get('reason')
        disposal_method = request.form.get('disposal_method')
        notes = request.form.get('notes', '').strip()

        errors = []
        if not food_name:
            errors.append("Food name cannot be empty.")
        if not category:
            errors.append("Category is required.")
        if not unit:
            errors.append("Unit is required.")
        if not date_str:
            errors.append("Date is required.")
        if not reason:
            errors.append("Reason is required.")
        if not disposal_method:
            errors.append("Disposal method is required.")
        
        quantity = 0
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
        except ValueError:
            errors.append("Quantity must be a valid number.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('add_waste.html', categories=CATEGORIES, units=UNITS, reasons=WASTE_REASONS, disposals=DISPOSAL_METHODS, form=request.form)

        waste_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        waste = WasteLog(user_id=current_user.id, 
            food_name=food_name,
            category=category,
            quantity=quantity,
            unit=unit,
            date=waste_date,
            reason=reason,
            disposal_method=disposal_method,
            notes=notes
        )
        db.session.add(waste)
        db.session.commit()
        flash('Waste recorded.', 'success')
        return redirect(url_for('waste_list'))

    return render_template('add_waste.html', categories=CATEGORIES, units=UNITS, reasons=WASTE_REASONS, disposals=DISPOSAL_METHODS, form={})

@app.route('/waste/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_waste(id):
    waste = WasteLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        food_name = request.form.get('food_name', '').strip()
        category = request.form.get('category')
        quantity_str = request.form.get('quantity', '')
        unit = request.form.get('unit')
        date_str = request.form.get('date')
        reason = request.form.get('reason')
        disposal_method = request.form.get('disposal_method')
        notes = request.form.get('notes', '').strip()

        errors = []
        if not food_name:
            errors.append("Food name cannot be empty.")
        if not category:
            errors.append("Category is required.")
        if not unit:
            errors.append("Unit is required.")
        if not date_str:
            errors.append("Date is required.")
        if not reason:
            errors.append("Reason is required.")
        if not disposal_method:
            errors.append("Disposal method is required.")
        
        quantity = 0
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
        except ValueError:
            errors.append("Quantity must be a valid number.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('edit_waste.html', waste=waste, categories=CATEGORIES, units=UNITS, reasons=WASTE_REASONS, disposals=DISPOSAL_METHODS)

        waste.food_name = food_name
        waste.category = category
        waste.quantity = quantity
        waste.unit = unit
        waste.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        waste.reason = reason
        waste.disposal_method = disposal_method
        waste.notes = notes

        db.session.commit()
        flash('Waste updated.', 'success')
        return redirect(url_for('waste_list'))

    return render_template('edit_waste.html', waste=waste, categories=CATEGORIES, units=UNITS, reasons=WASTE_REASONS, disposals=DISPOSAL_METHODS)

@app.route('/waste/<int:id>/delete', methods=['POST'])
@login_required
def delete_waste(id):
    waste = WasteLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(waste)
    db.session.commit()
    flash('Waste removed.', 'success')
    return redirect(url_for('waste_list'))

@app.route('/waste/analytics')
@login_required
def waste_analytics():
    all_wastes = WasteLog.query.filter_by(user_id=current_user.id).order_by(WasteLog.date.desc()).all()
    total_waste = len(all_wastes)
    
    if total_waste == 0:
        return render_template('waste_analytics.html', total_waste=0)
        
    cat_counts = Counter([w.category for w in all_wastes])
    reason_counts = Counter([w.reason for w in all_wastes])
    disp_counts = Counter([w.disposal_method for w in all_wastes])
    
    insights = {
        'total': total_waste,
        'most_category': cat_counts.most_common(1)[0][0] if cat_counts else "N/A",
        'most_reason': reason_counts.most_common(1)[0][0] if reason_counts else "N/A",
        'most_disposal': disp_counts.most_common(1)[0][0] if disp_counts else "N/A"
    }
    
    recent_wastes = all_wastes[:5]
    
    return render_template(
        'waste_analytics.html',
        total_waste=total_waste,
        insights=insights,
        cat_counts=cat_counts.items(),
        reason_counts=reason_counts.items(),
        disp_counts=disp_counts.items(),
        recent_wastes=recent_wastes
    )

@app.route('/meals')
@login_required
def meal_planner():
    # Use Soon section logic
    all_foods = FoodItem.query.filter_by(user_id=current_user.id).order_by(FoodItem.expiry_date.asc()).all()
    use_soon_foods = [f for f in all_foods if f.expiry_status in ['Use Today', 'Use Soon']]
    
    # Meal plans
    meals = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.plan_date.asc()).all()
    
    return render_template('meal_planner.html', use_soon_foods=use_soon_foods, meals=meals)

@app.route('/meals/add', methods=['GET', 'POST'])
@login_required
def add_meal():
    if request.method == 'POST':
        date_str = request.form.get('plan_date')
        meal_type = request.form.get('meal_type')
        meal_name = request.form.get('meal_name', '').strip()
        notes = request.form.get('notes', '').strip()
        
        errors = []
        if not date_str:
            errors.append("Date is required.")
        if not meal_type:
            errors.append("Meal type is required.")
        if not meal_name:
            errors.append("Meal name is required.")
            
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('add_meal.html', meal_types=MEAL_TYPES, form=request.form)
            
        plan_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        meal = MealPlan(user_id=current_user.id, 
            plan_date=plan_date,
            meal_type=meal_type,
            meal_name=meal_name,
            notes=notes
        )
        db.session.add(meal)
        db.session.commit()
        flash('Meal plan saved.', 'success')
        return redirect(url_for('meal_planner'))
        
    return render_template('add_meal.html', meal_types=MEAL_TYPES, form={})

@app.route('/meals/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_meal(id):
    meal = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        date_str = request.form.get('plan_date')
        meal_type = request.form.get('meal_type')
        meal_name = request.form.get('meal_name', '').strip()
        notes = request.form.get('notes', '').strip()
        
        errors = []
        if not date_str:
            errors.append("Date is required.")
        if not meal_type:
            errors.append("Meal type is required.")
        if not meal_name:
            errors.append("Meal name is required.")
            
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('edit_meal.html', meal=meal, meal_types=MEAL_TYPES)
            
        meal.plan_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        meal.meal_type = meal_type
        meal.meal_name = meal_name
        meal.notes = notes
        
        db.session.commit()
        flash('Meal plan updated.', 'success')
        return redirect(url_for('meal_planner'))
        
    return render_template('edit_meal.html', meal=meal, meal_types=MEAL_TYPES)

@app.route('/meals/<int:id>/delete', methods=['POST'])
@login_required
def delete_meal(id):
    meal = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(meal)
    db.session.commit()
    flash('Meal plan removed.', 'success')
    return redirect(url_for('meal_planner'))

@app.route('/tips')
def tips():
    return render_template('tips.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('register'))

        
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/service-worker.js')
def service_worker():
    from flask import send_from_directory
    response = send_from_directory('static', 'service-worker.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response
