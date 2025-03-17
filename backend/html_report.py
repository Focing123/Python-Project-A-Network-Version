import os
import webbrowser
from Units import *
from Building import *

def generate_html_report(players):
    # Calculate total units for proportion diagram
    total_units = sum(len(player.units) for player in players)
    
    # Generate random colors for players
    player_colors = [f"hsl({(i * 360) // len(players)}, 70%, 50%)" for i in range(len(players))]
    
    # Start of HTML content
    html_content = '''
    <html>
    <head>
        <title>Game Units, Buildings, and Resources Report</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; margin: 20px; }
            h1 { color: #444; text-align: center; }
            h2 { color: #444; }
            .player-section {
                background-color: #ffffff;
                padding: 20px;
                margin: 20px auto;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                max-width: 800px;
            }
            .info { margin-bottom: 20px; font-size: 14px; color: #666; }
            .collapsible {
                background-color: #007BFF;
                color: white;
                cursor: pointer;
                padding: 10px;
                width: 100%;
                border: none;
                text-align: left;
                outline: none;
                font-size: 16px;
                border-radius: 5px;
                margin-top: 10px;
            }
            .active, .collapsible:hover { background-color: #0056b3; }
            .content {
                padding: 0 18px;
                display: none;
                overflow: hidden;
                background-color: #f1f1f1;
                border-left: 3px solid #007BFF;
                margin-bottom: 10px;
                border-radius: 0 0 5px 5px;
            }
            .unit-info, .building-info {
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }
            .unit-info:last-child, .building-info:last-child { border-bottom: none; }
            .progress-bar {
                background-color: #e0e0e0;
                border-radius: 5px;
                overflow: hidden;
                width: 100%;
                height: 15px;
                margin-top: 5px;
            }
            .progress {
                height: 100%;
                background-color: #28a745;
                border-radius: 5px;
                width: 0%;
                transition: width 0.5s;
            }
            .unit-proportion-bar {
                width: 100%;
                height: 30px;
                background-color: #e0e0e0;
                border-radius: 5px;
                overflow: hidden;
                margin: 20px auto;
                display: flex;
                max-width: 800px;
            }
            .proportion-segment {
                height: 100%;
                transition: width 0.5s;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 12px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }
            .unit-proportion-legend {
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 10px;
                margin: 10px 0;
                max-width: 800px;
                margin: 10px auto;
            }
            .legend-item {
                display: flex;
                align-items: center;
                margin: 0 10px;
            }
            .legend-color {
                width: 20px;
                height: 20px;
                margin-right: 5px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1>Game Units, Buildings, and Resources Report</h1>
    '''
    
    # Add unit proportion diagram
    html_content += '<div class="unit-proportion-bar">'
    for i, player in enumerate(players):
        player_unit_count = len(player.units)
        if total_units > 0:
            proportion = (player_unit_count / total_units) * 100
            html_content += f'''
                <div class="proportion-segment" style="width: {proportion}%; background-color: {player_colors[i]};">
                    {proportion:.1f}%
                </div>
            '''
    html_content += '</div>'
    
    # Add legend
    html_content += '<div class="unit-proportion-legend">'
    for i, player in enumerate(players):
        html_content += f'''
            <div class="legend-item">
                <div class="legend-color" style="background-color: {player_colors[i]}"></div>
                <span>{player.name} ({len(player.units)} units)</span>
            </div>
        '''
    html_content += '</div>'

    # Generate player sections
    for i, player in enumerate(players):
        unit_categories = {
            'Villager': [], 'Swordsman': [], 'Horseman': [], 'Archer': []
        }
        building_categories = {
            'Town Center': [], 'House': [], 'Camp': [], 'Farm': [],
            'Barracks': [], 'Stable': [], 'Archery Range': [], 'Keep': []
        }

        # Categorize units
        for unit in player.units:
            if isinstance(unit, Villager): unit_categories['Villager'].append(unit)
            elif isinstance(unit, Swordsman): unit_categories['Swordsman'].append(unit)
            elif isinstance(unit, Horseman): unit_categories['Horseman'].append(unit)
            elif isinstance(unit, Archer): unit_categories['Archer'].append(unit)

        # Categorize buildings
        for building in player.buildings:
            if isinstance(building, TownCenter): building_categories['Town Center'].append(building)
            elif isinstance(building, House): building_categories['House'].append(building)
            elif isinstance(building, Camp): building_categories['Camp'].append(building)
            elif isinstance(building, Farm): building_categories['Farm'].append(building)
            elif isinstance(building, Barracks): building_categories['Barracks'].append(building)
            elif isinstance(building, Stable): building_categories['Stable'].append(building)
            elif isinstance(building, ArcheryRange): building_categories['Archery Range'].append(building)
            elif isinstance(building, Keep): building_categories['Keep'].append(building)

        max_population_build = sum(building.population_increase for building in player.buildings)
        
        # Generate player section
        # Ajouter une icône de tête de mort si le joueur n'a ni unités ni bâtiments
        icon = "💀" if not player.units and not player.buildings else ""
        html_content += f'''
        <div class="player-section">
            <h2>{player.name} {icon}</h2>
            <div class="info">
                <p>Population: {player.population}/{max_population_build}</p>
                <div class="progress-bar">
                    <div class="progress" style="width: {0 if max_population_build == 0 else player.population / max_population_build * 100}%;"></div>
                </div>
                <p>Resources | Wood: {player.owned_resources['Wood']} | Food: {player.owned_resources['Food']} | Gold: {player.owned_resources['Gold']}</p>
            </div>
            <button class="collapsible">Show Units</button>
            <div class="content">

        '''

        # Generate unit sections
        for category, unit_list in unit_categories.items():
            html_content += f'''
            <button class="collapsible">{category} ({len(unit_list)})</button>
            <div class="content">
            '''
            if unit_list:
                for unit in unit_list:
                    html_content += f'''
                    <div class="unit-info">
                        <h3>{unit.name} (HP: {unit.hp})</h3>
                        <p>Position: ({unit.position[0]:.2f}, {unit.position[1]:.2f})</p>
                        <p>Task: {unit.task}</p>
                    </div>
                    '''
            else:
                html_content += "<p>No units available</p>"
            html_content += "</div>"

        html_content += "</div>"

        # Generate building sections
        html_content += "<button class='collapsible'>Show Buildings</button><div class='content'>"
        for category, building_list in building_categories.items():
            html_content += f"<button class='collapsible'>{category} ({len(building_list)})</button><div class='content'>"
            if building_list:
                for building in building_list:
                    html_content += f'''
                    <div class='building-info'>
                        <h3>{building.name} (HP: {building.hp})</h3>
                        <p>Position: {building.position}</p>
                    </div>
                    '''
            else:
                html_content += "<p>No buildings available</p>"
            html_content += "</div>"

        html_content += "</div></div>"

    # Add JavaScript for collapsible sections
    html_content += '''
        <script>
            document.querySelectorAll('.collapsible').forEach((coll) => {
                coll.addEventListener('click', () => {
                    coll.classList.toggle('active');
                    const content = coll.nextElementSibling;
                    content.style.display = content.style.display === 'block' ? 'none' : 'block';
                });
            });
        </script>
    </body>
    </html>
    '''

    # Write to file and open in browser
    report_file = "../assets/annex/game_units_report.html"
    with open(report_file, "w", encoding="utf-8") as file:
        file.write(html_content)

    print("HTML report generated: game_units_report.html")
    webbrowser.open(f'file://{os.path.realpath(report_file)}')