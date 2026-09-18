from functools import wraps
import re
from flask import current_app as app, render_template, request, redirect, url_for, flash, abort
from collections import Counter
from app import db
from app.models import FoodItem, WasteLog, MealPlan, User, Feedback, ActivityLog
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        admin_email = app.config.get('ADMIN_EMAIL')
        if not admin_email or current_user.email.lower() != admin_email:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def is_admin_user():
    return (
        current_user.is_authenticated
        and app.config.get('ADMIN_EMAIL')
        and current_user.email.lower() == app.config.get('ADMIN_EMAIL', '').strip().lower()
    )

def household_user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if is_admin_user():
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(user_id, action, entity_type):
    try:
        log = ActivityLog(user_id=user_id, action=action, entity_type=entity_type)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()



@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        if is_admin_user():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
@household_user_required
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
@household_user_required
def food_list():
    foods = FoodItem.query.filter_by(user_id=current_user.id).order_by(FoodItem.expiry_date.asc()).all()
    return render_template('food_list.html', foods=foods)

@app.route('/food/add', methods=['GET', 'POST'])
@login_required
@household_user_required
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
@household_user_required
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
@household_user_required
def delete_food(id):
    food = FoodItem.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(food)
    db.session.commit()

    flash('Food removed.', 'success')
    return redirect(url_for('food_list'))

@app.route('/waste')
@login_required
@household_user_required
def waste_list():
    wastes = WasteLog.query.filter_by(user_id=current_user.id).order_by(WasteLog.date.desc()).all()
    return render_template('waste_list.html', wastes=wastes)

@app.route('/waste/add', methods=['GET', 'POST'])
@login_required
@household_user_required
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
@household_user_required
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
@household_user_required
def delete_waste(id):
    waste = WasteLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(waste)
    db.session.commit()

    flash('Waste removed.', 'success')
    return redirect(url_for('waste_list'))

@app.route('/waste/analytics')
@login_required
@household_user_required
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

    # Calculations for 30 days pattern
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)
    
    current_period = [w for w in all_wastes if w.date >= thirty_days_ago]
    prev_period = [w for w in all_wastes if sixty_days_ago <= w.date < thirty_days_ago]
    
    trend = {
        'current': len(current_period),
        'previous': len(prev_period),
        'message': 'Similar number of waste events.'
    }
    if trend['current'] < trend['previous']:
        trend['message'] = "Fewer waste events than the previous period."
    elif trend['current'] > trend['previous']:
        trend['message'] = "More waste events were recorded than the previous period."
        
    # Generate Recommendation
    recommendation = "Review Food Saving Tips for general advice."
    priority_action = None
    if insights['most_reason'] == "More food was cooked than needed":
        recommendation = "Try preparing slightly smaller portions. Check previous leftovers before cooking another full meal."
        priority_action = "Cook smaller portions."
    elif insights['most_reason'] == "Too much food was bought":
        recommendation = "Check My Food before shopping and buy only what is needed."
        priority_action = "Review inventory before shopping."
    elif insights['most_reason'] == "Food expired":
        recommendation = "Check the Use Soon section regularly and keep older items visible."
        priority_action = "Use food nearing expiry before buying more."
    elif insights['most_reason'] == "Food was forgotten":
        recommendation = "Keep food that should be used soon in an easy-to-see place and check your dashboard before planning meals."
        priority_action = "Organize storage to keep older items visible."
    elif insights['most_reason'] == "Meal plans changed":
        recommendation = "Plan smaller or flexible meals when household schedules may change."
        priority_action = "Make flexible meal plans."
    elif insights['most_reason'] == "Leftover was not used":
        recommendation = "Check usable leftovers before preparing a new meal."
        priority_action = "Use safely stored leftovers in a suitable next meal."
    elif insights['most_reason'] == "Food was stored incorrectly":
        recommendation = "Review Food Saving Tips and follow suitable storage instructions."
        priority_action = "Check storage instructions."
    elif insights['most_reason'] == "Food quality became poor":
        recommendation = "Buy smaller quantities of highly perishable food and use older items first."
        priority_action = "Buy perishables in smaller batches."
    
    recent_wastes = all_wastes[:5]
    
    return render_template(
        'waste_analytics.html',
        total_waste=total_waste,
        insights=insights,
        cat_counts=cat_counts.items(),
        reason_counts=reason_counts.items(),
        disp_counts=disp_counts.items(),
        recent_wastes=recent_wastes,
        trend=trend,
        recommendation=recommendation,
        priority_action=priority_action
    )

@app.route('/meals')
@login_required
@household_user_required
def meal_planner():
    # Use Soon section logic
    all_foods = FoodItem.query.filter_by(user_id=current_user.id).order_by(FoodItem.expiry_date.asc()).all()
    use_soon_foods = [f for f in all_foods if f.expiry_status in ['Use Today', 'Use Soon']]
    
    # Meal plans
    meals = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.plan_date.asc()).all()
    
    return render_template('meal_planner.html', use_soon_foods=use_soon_foods, meals=meals)

@app.route('/meals/add', methods=['GET', 'POST'])
@login_required
@household_user_required
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
@household_user_required
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
@household_user_required
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
        if is_admin_user():
            return redirect(url_for('admin_dashboard'))
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
        if is_admin_user():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)

            if is_admin_user():
                return redirect(url_for('admin_dashboard'))
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


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
@household_user_required
def feedback():
    if request.method == 'POST':
        rating_str = request.form.get('rating')
        category = request.form.get('category')
        message = request.form.get('message', '').strip()
        
        if not rating_str or not category or not message:
            flash("All fields are required.", "danger")
            return redirect(url_for('feedback'))
            
        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                raise ValueError()
        except ValueError:
            flash("Please select a valid rating.", "danger")
            return redirect(url_for('feedback'))
            
        allowed_categories = ['Suggestion', 'Usability', 'Feature Request', 'Other']
        if category not in allowed_categories:
            flash("Please select a valid category.", "danger")
            return redirect(url_for('feedback'))
            
        if len(message) > 2000:
            flash("Message is too long (max 2000 characters).", "danger")
            return redirect(url_for('feedback'))
            
        fb = Feedback(user_id=current_user.id, rating=rating, category=category, message=message)
        db.session.add(fb)
        db.session.commit()

        flash('Thank you for your feedback.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('feedback.html')

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    admin_email = app.config.get('ADMIN_EMAIL', '').strip().lower()
    admin_user = User.query.filter_by(email=admin_email).first()
    admin_id = admin_user.id if admin_user else -1
    
    # Base query filters excluding admin
    household_users_count = User.query.filter(User.id != admin_id).count()
    total_food = FoodItem.query.filter(FoodItem.user_id != admin_id).count()
    total_meals = MealPlan.query.filter(MealPlan.user_id != admin_id).count()
    
    all_wastes = WasteLog.query.filter(WasteLog.user_id != admin_id).all()
    total_wastes = len(all_wastes)
    
    total_feedback = Feedback.query.filter(Feedback.user_id != admin_id).count()
    new_feedback = Feedback.query.filter(Feedback.user_id != admin_id, Feedback.status == 'New').count()
    
    # Engagement Overview (Distinct Users excluding admin)
    users_using_food = db.session.query(FoodItem.user_id).filter(FoodItem.user_id != admin_id).distinct().count()
    users_using_meals = db.session.query(MealPlan.user_id).filter(MealPlan.user_id != admin_id).distinct().count()
    users_using_waste = db.session.query(WasteLog.user_id).filter(WasteLog.user_id != admin_id).distinct().count()
    users_using_feedback = db.session.query(Feedback.user_id).filter(Feedback.user_id != admin_id).distinct().count()
    
    engagement = {
        'food': users_using_food,
        'meals': users_using_meals,
        'waste': users_using_waste,
        'feedback': users_using_feedback,
        'food_pct': round((users_using_food / household_users_count * 100) if household_users_count > 0 else 0),
        'meals_pct': round((users_using_meals / household_users_count * 100) if household_users_count > 0 else 0),
        'waste_pct': round((users_using_waste / household_users_count * 100) if household_users_count > 0 else 0),
        'feedback_pct': round((users_using_feedback / household_users_count * 100) if household_users_count > 0 else 0),
    }
    
    recent_feedback = Feedback.query.filter(Feedback.user_id != admin_id).order_by(Feedback.created_at.desc()).limit(20).all()
    
    # Community Waste Insights
    cat_counts = Counter([w.category for w in all_wastes])
    reason_counts = Counter([w.reason for w in all_wastes])
    disp_counts = Counter([w.disposal_method for w in all_wastes])
    
    most_category = cat_counts.most_common(1)[0][0] if cat_counts else "N/A"
    most_reason = reason_counts.most_common(1)[0][0] if reason_counts else "N/A"
    most_disposal = disp_counts.most_common(1)[0][0] if disp_counts else "N/A"
    
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)
    
    current_period = [w for w in all_wastes if w.date >= thirty_days_ago]
    prev_period = [w for w in all_wastes if sixty_days_ago <= w.date < thirty_days_ago]
    
    trend = {
        'current': len(current_period),
        'previous': len(prev_period)
    }
    
    community_focus = None
    if most_reason == "More food was cooked than needed":
        community_focus = "Encourage households to plan portion sizes and check leftovers before cooking."
    elif most_reason == "Too much food was bought":
        community_focus = "Encourage households to check existing food before shopping."
    elif most_reason == "Food expired":
        community_focus = "Encourage regular expiry checks and use-soon habits."
    elif most_reason != "N/A":
        community_focus = "Monitor trends closely to determine targeted intervention."
    
    community_insights = {
        'most_category': most_category,
        'most_reason': most_reason,
        'most_disposal': most_disposal,
        'trend': trend,
        'community_focus': community_focus
    }
    
    return render_template('admin.html', 
        stats={
            'users': household_users_count,
            'food': total_food,
            'meals': total_meals,
            'wastes': total_wastes,
            'feedback': total_feedback,
            'new_feedback': new_feedback
        },
        engagement=engagement,
        recent_feedback=recent_feedback,
        community_insights=community_insights
    )

@app.route('/admin/feedback/<int:id>/review', methods=['POST'])
@login_required
@admin_required
def admin_review_feedback(id):
    fb = Feedback.query.get_or_404(id)
    fb.status = 'Reviewed'
    db.session.commit()

    flash('Feedback marked as reviewed.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/account')
@login_required
@household_user_required
def account():
    return render_template('account.html')

@app.route('/account/delete', methods=['POST'])
@login_required
@household_user_required
def delete_account():
    password = request.form.get('password')
    confirmation = request.form.get('confirmation')
    
    if not password:
        flash("Please enter your password.", "danger")
        return redirect(url_for('account'))
        
    if confirmation != "DELETE":
        flash("Please type DELETE to confirm.", "danger")
        return redirect(url_for('account'))
        
    if not current_user.check_password(password):
        flash("Incorrect password.", "danger")
        return redirect(url_for('account'))
        
    user_id = current_user.id
    
    try:
        Feedback.query.filter_by(user_id=user_id).delete()
        ActivityLog.query.filter_by(user_id=user_id).delete()
        FoodItem.query.filter_by(user_id=user_id).delete()
        MealPlan.query.filter_by(user_id=user_id).delete()
        WasteLog.query.filter_by(user_id=user_id).delete()
        
        user_record = User.query.get(user_id)
        if user_record:
            db.session.delete(user_record)
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting your account.", "danger")
        return redirect(url_for('account'))
        
    logout_user()
    flash("Your account and FoodWise data have been deleted.", "success")
    return redirect(url_for('index'))
