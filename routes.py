# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, get_flashed_messages, session
from flask_login import current_user, login_required, login_user, logout_user
from models import db, User, Player, Birdie, Course, HistoricalTotal, Eagle
from sqlalchemy.sql import func, case, and_, or_
from datetime import datetime, timedelta

# Create a Blueprint
bp = Blueprint('main', __name__)

print("Routes file imported")

def clear_flash_messages():
    # Clear any existing flash messages
    get_flashed_messages(with_categories=True)

@bp.route("/test")
def test():
    return "Test route is working!"

@bp.route("/")
def home():
    return redirect(url_for('main.leaderboard'))

@bp.route("/leaderboard")
def leaderboard():
    current_year = datetime.now().year
    
    # Get all players
    players = Player.query.all()
    
    # Calculate stats for each player
    player_stats = []
    for player in players:
        # Get birdies and eagles for current year only
        birdies = Birdie.query.filter_by(player_id=player.id, year=current_year).all()
        eagles = Eagle.query.filter_by(player_id=player.id, year=current_year).all()
        
        # Check for recent birdies (within last 2 days)
        two_days_ago = datetime.now().date() - timedelta(days=2)
        recent_birdies = [b for b in birdies if b.date >= two_days_ago]
        
        # Add one birdie emoji for each recent birdie
        emoji = "🐦" * len(recent_birdies)
        
        player_stats.append({
            'name': player.name,
            'id': player.id,
            'birdies': len(birdies),
            'eagles': len(eagles),
            'total': len(birdies) + len(eagles),
            'emoji': emoji
        })
    
    # Sort by total birdies+eagles
    player_stats.sort(key=lambda x: x['total'], reverse=True)
    
    print("\nPlayers data for year", current_year)
    for stat in player_stats:
        print(f"{stat['name']}: Birdies={stat['birdies']}, Eagles={stat['eagles']}, Emojis={stat['emoji']}")
    
    return render_template('leaderboard.html', players=player_stats, year=current_year)

@bp.route("/add_player", methods=["GET", "POST"])
def add_player():
    if request.method == "POST":
        name = request.form["name"].strip()
        existing_player = Player.query.filter(func.lower(Player.name) == func.lower(name)).first()
        if existing_player:
            flash("Player with this name already exists.", "error")
            return redirect(url_for("add_player"))
        new_player = Player(name=name)
        db.session.add(new_player)
        db.session.commit()
        flash("Player added successfully!", "success")
        return redirect(url_for("main.leaderboard"))
    clear_flash_messages()
    return render_template("add_player.html")

@bp.route("/add_birdie", methods=["GET", "POST"])
def add_birdie():
    if request.method == "POST":
        try:
            player_id = request.form.get("player_id")
            course_id = request.form.get("course_id")
            date_str = request.form.get("date")
            is_eagle = request.form.get("is_eagle") == "on"
            
            # Parse the date
            date = datetime.strptime(date_str, "%Y-%m-%d")
            current_year = datetime.now().year
            
            # Check if the date is from a previous year
            if date.year < current_year:
                flash("Error: Cannot add birdies from previous years!", "error")
                return redirect(url_for("add_birdie"))
            
            # Check if the date is in the future
            if date.date() > datetime.now().date():
                flash("Error: Cannot add birdies for future dates!", "error")
                return redirect(url_for("add_birdie"))

            # Get the player first
            player = Player.query.get(player_id)
            
            # Create the birdie/eagle record
            birdie = Birdie(
                player_id=player_id, 
                course_id=course_id, 
                date=date, 
                year=current_year,
                is_eagle=is_eagle
            )
            
            # If it's an eagle, update the permanent eagle emojis
            if is_eagle:
                # Count total eagles for this player this year
                eagle_count = Birdie.query.filter_by(
                    player_id=player_id,
                    year=current_year,
                    is_eagle=True
                ).count()
                
                # Add one for the new eagle we're adding
                eagle_count += 1
                
                # Update player's permanent emojis to match total eagle count
                player.permanent_emojis = "🦅" * eagle_count
            
            db.session.add(birdie)
            db.session.commit()
            flash("Score added successfully!", "success")
            return redirect(url_for("main.leaderboard"))
        except ValueError:
            flash("Error: Invalid date format!", "error")
            return redirect(url_for("add_birdie"))
        except Exception as e:
            print(f"Error adding score: {e}")
            flash("An error occurred while adding the score.", "error")
            return redirect(url_for("add_birdie"))

    players = Player.query.all()
    courses = Course.query.all()
    return render_template("add_birdie.html", players=players, courses=courses)

@bp.route("/add_course", methods=['POST'])
@login_required
def add_course():
    name = request.form.get('name')
    if not name:
        flash('Course name is required')
        return redirect(url_for('main.admin_dashboard'))
    
    # Check if course already exists
    existing_course = Course.query.filter_by(name=name).first()
    if existing_course:
        flash('A course with that name already exists')
        return redirect(url_for('main.admin_dashboard'))
    
    # Create new course
    course = Course(name=name)
    db.session.add(course)
    db.session.commit()
    
    flash('Course added successfully')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/players")
def get_players():
    players = Player.query.all()
    players_list = [player.to_dict() for player in players]
    return jsonify(players=players_list)

@bp.route("/player/<int:player_id>")
def player_birdie_records(player_id):
    player = Player.query.get_or_404(player_id)
    current_year = datetime.now().year
    
    # Get all birdies for the player for the current year
    birdies = db.session.query(
        Birdie
    ).filter_by(
        player_id=player_id,
        year=current_year
    ).order_by(Birdie.date.desc()).all()
    
    # Convert string dates to datetime objects if needed
    for birdie in birdies:
        if isinstance(birdie.date, str):
            birdie.date = datetime.strptime(birdie.date, '%Y-%m-%d')
    
    return render_template(
        "player_birdie_records.html",
        player=player,
        birdies=birdies,
        year=current_year
    )

@bp.route("/player/<int:player_id>")
def player_details(player_id):
    player = Player.query.get_or_404(player_id)
    current_year = datetime.now().year
    
    # Get all birdies for the player for the current year
    birdies = Birdie.query.filter_by(
        player_id=player_id,
        year=current_year
    ).order_by(Birdie.date.desc()).all()
    
    # Count eagles
    eagle_count = sum(1 for birdie in birdies if birdie.is_eagle)
    
    return render_template(
        "player_details.html",
        player=player,
        birdies=birdies,
        eagle_count=eagle_count,
        year=current_year
    )

@bp.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Logged in successfully.')
            return redirect(url_for('main.admin_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.leaderboard'))

@bp.route("/admin")
@login_required
def admin_dashboard():
    players = Player.query.all()
    courses = Course.query.all()
    # Print debug information
    for player in players:
        print(f"Player: {player.name}, Has Trophy: {player.has_trophy}")
    return render_template("admin_dashboard.html", players=players, courses=courses)

@bp.route("/admin/player_birdies", methods=["GET"])
def admin_player_birdies():
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    player_id = request.args.get("player_id")
    selected_player = Player.query.get_or_404(player_id)
    birdies = Birdie.query.filter_by(player_id=player_id).all()
    players = Player.query.all()
    courses = Course.query.all()
    return render_template("admin_dashboard.html", players=players, courses=courses, birdies=birdies, selected_player=selected_player)

@bp.route("/delete_player/<int:player_id>")
@login_required
def delete_player(player_id):
    # Check if user is logged in again
    if not current_user.is_authenticated:
        flash('Please log in to access this page')
        return redirect(url_for('login'))
    
    player = Player.query.get_or_404(player_id)
    
    # Delete all birdies for this player first
    Birdie.query.filter_by(player_id=player_id).delete()
    
    # Then delete the player
    db.session.delete(player)
    db.session.commit()
    
    flash(f'Player {player.name} has been deleted')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/delete_course/<int:course_id>")
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # First delete all birdies associated with this course
    Birdie.query.filter(Birdie.course_id == course_id).delete()
    
    # Then delete the course
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course {course.name} has been deleted.')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/delete_birdie/<int:birdie_id>", methods=['POST'])
def delete_birdie(birdie_id):
    birdie = Birdie.query.get_or_404(birdie_id)
    player_id = birdie.player_id
    
    # If it's an eagle being deleted, update permanent_emojis
    if birdie.is_eagle:
        player = Player.query.get(player_id)
        if player.permanent_emojis and "🦅" in player.permanent_emojis:
            player.permanent_emojis = player.permanent_emojis.replace("🦅", "", 1)
            if not player.permanent_emojis.strip():  # If no emojis left
                player.permanent_emojis = None
    
    db.session.delete(birdie)
    db.session.commit()
    
    flash("Birdie deleted successfully", "success")
    return redirect(url_for('main.player_birdie_records', player_id=player_id))

@bp.route("/admin/edit_player/<int:player_id>", methods=["POST"])
def edit_player(player_id):
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    player = Player.query.get_or_404(player_id)
    player.name = request.form["name"].strip()
    db.session.commit()
    flash("Player name updated successfully!", "success")
    return redirect(url_for("main.admin_dashboard"))

@bp.route("/admin/edit_course/<int:course_id>", methods=["POST"])
def edit_course(course_id):
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    course = Course.query.get_or_404(course_id)
    course.name = request.form["name"].strip()
    db.session.commit()
    flash("Course name updated successfully!", "success")
    return redirect(url_for("main.admin_dashboard"))

@bp.route("/admin/edit_birdie/<int:birdie_id>", methods=["POST"])
def edit_birdie(birdie_id):
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    birdie = Birdie.query.get_or_404(birdie_id)
    birdie.date = datetime.strptime(request.form["date"], "%Y-%m-%d")
    db.session.commit()
    flash("Birdie date updated successfully!", "success")
    return redirect(url_for("main.admin_player_birdies", player_id=birdie.player_id))

@bp.route("/add_emoji", methods=["GET", "POST"])
def add_emoji():
    if request.method == "POST":
        player_id = request.form["player_id"]
        emoji = request.form["emoji"]
        player = Player.query.get_or_404(player_id)
        if player.permanent_emojis is None:
            player.permanent_emojis = ""
        player.permanent_emojis += emoji
        db.session.commit()
        flash("Emoji added successfully!", "success")
        return redirect(url_for("main.leaderboard"))
    players = Player.query.all()
    return render_template("add_emoji.html", players=players)

@bp.route("/history", methods=["GET"])
def history():
    current_year = datetime.now().year
    selected_year = request.args.get('year', current_year, type=int)
    
    if selected_year == current_year:
        # Current year query stays the same
        players = db.session.query(
            Player,
            func.count(Birdie.id).label('birdie_count'),
            func.sum(case((Birdie.is_eagle == True, 1), else_=0)).label('eagle_count')
        ).outerjoin(
            Birdie, 
            (Player.id == Birdie.player_id) & (Birdie.year == selected_year)
        ).group_by(Player.id).having(
            func.count(Birdie.id) > 0
        ).all()
    else:
        # Historical query now uses total_eagles and includes has_trophy
        players = db.session.query(
            Player,
            HistoricalTotal.total_birdies.label('birdie_count'),
            HistoricalTotal.total_eagles.label('eagle_count'),
            HistoricalTotal.has_trophy.label('has_trophy')
        ).join(
            HistoricalTotal,
            (Player.id == HistoricalTotal.player_id) & 
            (HistoricalTotal.year == selected_year)
        ).filter(
            db.or_(
                HistoricalTotal.total_birdies > 0,
                HistoricalTotal.total_eagles > 0
            )
        ).group_by(Player.id).all()
    
    print(f"\nPlayers data for year {selected_year}:")  # Debug print
    
    # Create list of tuples with player data
    leaderboard = []
    for player_data in players:
        if selected_year == current_year:
            player, birdie_count, eagle_count = player_data
            has_trophy = "🏆" in (player.permanent_emojis or "")
        else:
            player, birdie_count, eagle_count, has_trophy = player_data
        
        # Create year-specific emojis
        year_emojis = "🦅" * int(eagle_count or 0)  # Eagles for the specific year
        if has_trophy:  # Add trophy if player won that year
            year_emojis += "🏆"
        
        print(f"{player.name}: Birdies={birdie_count}, Eagles={eagle_count}, Trophy={has_trophy}, Emojis={year_emojis}")  # Debug print
        
        leaderboard.append((
            player.name,
            birdie_count,
            player.id,
            year_emojis
        ))
    
    # Sort by birdie count (descending)
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)
    
    # Create ranked leaderboard with tie handling
    ranked_leaderboard = []
    previous_score = None
    rank_counter = 1
    
    for i, entry in enumerate(sorted_leaderboard):
        current_score = entry[1]
        
        if i == 0:
            # First player
            rank_display = str(rank_counter)
        elif current_score == previous_score:
            # Same score as previous player - it's a tie
            rank_display = f"T{rank_counter}"
            # Update previous player's rank to show tie
            if len(ranked_leaderboard) > 0 and not ranked_leaderboard[-1][0].startswith('T'):
                prev_entry = ranked_leaderboard[-1]
                ranked_leaderboard[-1] = (f"T{rank_counter}", *prev_entry[1:])
        else:
            # Different score from previous player
            rank_counter = i + 1
            rank_display = str(rank_counter)
        
        ranked_leaderboard.append((rank_display,) + entry)
        previous_score = current_score

    # Get list of available years
    db_years = db.session.query(
        db.distinct(Birdie.year)
    ).filter(
        Birdie.year.isnot(None)
    ).union(
        db.session.query(
            db.distinct(HistoricalTotal.year)
        ).filter(
            HistoricalTotal.year.isnot(None),
            db.or_(
                HistoricalTotal.total_birdies > 0,
                HistoricalTotal.total_eagles > 0
            )
        )
    ).all()
    
    years = [year[0] for year in db_years]
    
    # Always include current year
    if current_year not in years:
        years.append(current_year)
    
    # Sort years in descending order
    years = sorted(list(set(years)), reverse=True)

    return render_template(
        "history.html", 
        leaderboard=ranked_leaderboard,
        years=years, 
        selected_year=selected_year
    )

@bp.route("/add_trophy", methods=["GET", "POST"])
def add_trophy():
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            player_id = request.form.get("player_id")
            player = Player.query.get(player_id)
            
            if player:
                # Add trophy emoji if player doesn't already have one
                if "🏆" not in (player.permanent_emojis or ""):
                    player.permanent_emojis = (player.permanent_emojis or "") + "🏆"
                    db.session.commit()
                    flash(f"Trophy added to {player.name}!", "success")
                else:
                    flash(f"{player.name} already has a trophy!", "info")
            
            return redirect(url_for("main.leaderboard"))
        except Exception as e:
            print(f"Error adding trophy: {e}")
            flash("An error occurred while adding the trophy.", "error")
    
    players = Player.query.all()
    return render_template("add_trophy.html", players=players)

@bp.route("/add_historical_totals", methods=['GET', 'POST'])
@login_required
def add_historical_totals():
    current_year = datetime.now().year
    selected_year = 2024  # Default to 2024
    years = range(2020, current_year + 1)
    if not current_user.is_authenticated:
        return redirect(url_for("main.login"))

    if request.method == 'POST':
        player_id = request.form.get('player_id')
        year = request.form.get('year')
        birdies = request.form.get('birdies')
        eagles = request.form.get('eagles')

        historical_total = HistoricalTotal(
            player_id=player_id,
            year=year,
            birdies=birdies,
            eagles=eagles
        )
        db.session.add(historical_total)
        db.session.commit()

        flash('Historical totals added successfully!')
        return redirect(url_for('main.admin_dashboard'))

    players = Player.query.all()
    return render_template('add_historical_totals.html', 
        players=players,
        current_year=current_year,
        selected_year=selected_year,
        years=years)  
    

    if request.method == "POST":
        try:
            print("\nForm Data:")
            for key, value in request.form.items():
                print(f"{key}: {value}")
            
            year = int(request.form.get("year"))
            print(f"\nProcessing year: {year}")
            
            if year >= current_year:
                flash("Cannot add historical records for current or future years!", "error")
                return redirect(url_for("add_historical_totals"))
            
            # Get all player IDs and their totals from the form
            for key, value in request.form.items():
                if key.startswith('birdies_'):
                    player_id = int(key.split('_')[1])
                    total_birdies = int(value) if value else 0
                    total_eagles = int(request.form.get(f'eagles_{player_id}', 0))
                    has_trophy = request.form.get(f'trophy_{player_id}') == 'on'
                    
                    print(f"\nProcessing player {player_id}:")
                    print(f"Birdies: {total_birdies}")
                    print(f"Eagles: {total_eagles}")
                    print(f"Trophy: {has_trophy}")
                    
                    # Update or create the historical total
                    historical_total = HistoricalTotal.query.filter_by(
                        player_id=player_id,
                        year=year
                    ).first()
                    
                    if historical_total:
                        print(f"Updating existing record")
                        historical_total.total_birdies = total_birdies
                        historical_total.total_eagles = total_eagles
                        historical_total.has_trophy = has_trophy
                        print(f"Updated values - Birdies: {historical_total.total_birdies}, Eagles: {historical_total.total_eagles}, Trophy: {historical_total.has_trophy}")
                    else:
                        print(f"Creating new record")
                        historical_total = HistoricalTotal(
                            player_id=player_id,
                            year=year,
                            total_birdies=total_birdies,
                            total_eagles=total_eagles,
                            has_trophy=has_trophy
                        )
                        db.session.add(historical_total)
                        print("New record added to session")
            
            print("\nCommitting to database...")
            db.session.commit()
            print("Commit successful!")
            
            # Verify the data was saved
            print("\nVerifying saved data:")
            saved_records = HistoricalTotal.query.filter_by(year=year).all()
            for record in saved_records:
                player = Player.query.get(record.player_id)
                print(f"Player: {player.name}, Birdies: {record.total_birdies}, Eagles: {record.total_eagles}, Trophy: {record.has_trophy}")
            
            flash(f"Historical totals updated for {year}", "success")
            return redirect(url_for("main.history", year=year))

        except Exception as e:
            print(f"\nError adding historical totals: {str(e)}")
            import traceback
            print(traceback.format_exc())
            flash("An error occurred while adding historical totals.", "error")
            return redirect(url_for("add_historical_totals"))

    # For GET request, prepare the form
    players = Player.query.all()
    available_years = list(range(current_year - 5, current_year))  # Last 5 years
    
    return render_template(
        "add_historical_totals.html", 
        players=players,
        available_years=available_years,
        selected_year=selected_year
    )

@bp.route("/debug_eagles/<int:player_id>")
def debug_eagles(player_id):
    current_year = datetime.now().year
    eagles = Birdie.query.filter_by(
        player_id=player_id,
        year=current_year,
        is_eagle=True
    ).all()
    
    result = []
    for eagle in eagles:
        result.append({
            'id': eagle.id,
            'date': eagle.date,
            'course': eagle.course.name,
            'is_eagle': eagle.is_eagle
        })
    
    return jsonify(result)

@bp.route("/debug_player/<int:player_id>")
def debug_player(player_id):
    player = Player.query.get_or_404(player_id)
    return jsonify({
        'name': player.name,
        'permanent_emojis': player.permanent_emojis,
        'id': player.id
    })

@bp.route("/reset_permanent_emojis/<int:player_id>")
def reset_permanent_emojis(player_id):
    player = Player.query.get_or_404(player_id)
    player.permanent_emojis = None  # or "" if you prefer
    db.session.commit()
    flash("Permanent emojis have been reset", "success")
    return redirect(url_for('main.leaderboard'))

@bp.route("/trends")
def trends():
    # Get all years from both current and historical data
    years = db.session.query(
        db.distinct(Birdie.year)
    ).filter(
        Birdie.year.isnot(None)
    ).union(
        db.session.query(
            db.distinct(HistoricalTotal.year)
        ).filter(
            HistoricalTotal.year.isnot(None)
        )
    ).all()
    
    years = sorted([year[0] for year in years], reverse=True)
    
    # Get all players
    players = Player.query.all()
    
    # Get yearly totals for each player
    player_stats = {}
    for player in players:
        yearly_stats = []
        for year in years:
            # Get current year stats
            if year == datetime.now().year:
                stats = db.session.query(
                    func.count(Birdie.id).label('birdies'),
                    func.sum(case((Birdie.is_eagle == True, 1), else_=0)).label('eagles')
                ).filter(
                    Birdie.player_id == player.id,
                    Birdie.year == year
                ).first()
                birdies = stats[0] or 0
                eagles = stats[1] or 0
            else:
                # Get historical stats
                historical = HistoricalTotal.query.filter_by(
                    player_id=player.id,
                    year=year
                ).first()
                birdies = historical.total_birdies if historical else 0
                eagles = historical.total_eagles if historical else 0
            
            yearly_stats.append({
                'year': year,
                'birdies': birdies,
                'eagles': eagles,
                'total': birdies + eagles
            })
        
        player_stats[player.name] = yearly_stats
    
    print("Debug - Years:", years)
    print("Debug - Players:", [p.name for p in players])
    print("Debug - Player Stats:", player_stats)
    
    return render_template(
        'trends.html',
        years=years,
        players=players,
        player_stats=player_stats
    )

@bp.route("/delete_trophy/<int:player_id>")
@login_required
def delete_trophy(player_id):
    player = Player.query.get_or_404(player_id)
    if player.has_trophy:
        player.has_trophy = False
        db.session.commit()
        flash(f'Trophy removed from {player.name}')
    else:
        flash(f'{player.name} does not have a trophy')
    return redirect(url_for('admin_dashboard'))