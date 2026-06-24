from datetime import datetime

def get_month_name_fr(year_month_str):
    mois_francais = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]
    year, month = year_month_str.split('-')
    month_num = int(month)
    month_name = mois_francais[month_num - 1]
    return f"{month_name} {year}"
