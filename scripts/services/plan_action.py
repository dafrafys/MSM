from sqlalchemy import text
import pandas as pd
import datetime

def get_all_personnel(engine):
    query = text("""
        SELECT "Personnel_Id", "Nom", "Prenom"
        FROM public."Personnel"
        WHERE "Role" IN ('Chef I', 'Chef II', 'Chef III' )
        ORDER BY "Nom", "Prenom"
    """)
    df = pd.read_sql(query, engine)
    # Retourner sous forme liste dict avec id + nom complet
    return [
        {"id": row["Personnel_Id"], "name": f"{row['Nom']} {row['Prenom']}"}
        for _, row in df.iterrows()
    ]

def insert_plan_action(engine, form):
    """
    Insère un plan d'action simple dans la table plan_action.
    form doit contenir : personnel_id, type, action, sujet, date, statut, commentaire, delai_initiale, delai_revise.
    Renvoie (success: bool, message: str)
    """
    try:
        personnel_id   = form['personnel_id']
        type_          = form.get('type')
        action         = form['action']
        sujet          = form.get('sujet')

        date_str = form.get('date')
        if date_str:
            date_ = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date_ = datetime.date.today()

        statut         = form.get('statut')
        if statut is None or statut == '':
            statut = 0.25  # Valeur par défaut

        commentaire    = form.get('commentaire')

        delai_str = form.get('delai_initiale')
        if delai_str:
            delai_initiale = datetime.datetime.strptime(delai_str, '%Y-%m-%d').date()
        else:
            if date_.weekday() == 4:  # vendredi
                delai_initiale = date_ + datetime.timedelta(days=3)
            else:
                delai_initiale = date_ + datetime.timedelta(days=1)

        delai_revise   = form.get('delai_revise')

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO public.plan_action (
                    personnel_id, type, action, sujet, date, statut, commentaire, delai_initiale, delai_revise
                ) VALUES (
                    :personnel_id, :type_, :action, :sujet, :date_, :statut, :commentaire, :delai_initiale, :delai_revise
                )
            """), {
                "personnel_id": personnel_id,
                "type_": type_,
                "action": action,
                "sujet": sujet,
                "date_": date_.isoformat(),
                "statut": float(statut),
                "commentaire": commentaire,
                "delai_initiale": delai_initiale.isoformat(),
                "delai_revise": delai_revise
            })
        return True, "Plan d'action inséré avec succès"
    except Exception as e:
        return False, str(e)

def update_plan_action(engine, form):
    """
    Met à jour uniquement le commentaire et le délai révisé d'un plan d'action identifié par plan_id.
    form doit contenir : plan_id, commentaire, delai_revise.
    Renvoie (success: bool, message: str)
    """
    try:
        plan_id = form['plan_id']
        commentaire = form.get('commentaire')
        delai_revise = form.get('delai_revise')
        statut = form.get('statut')

        if commentaire == "":
            commentaire = None
        if delai_revise == "":
            delai_revise = None

        if statut is not None and float(statut) == 1.0:
            # statut = 1 -> mettre la date de clôture
            update_query = """
            UPDATE public.plan_action
            SET commentaire = :commentaire,
                delai_revise = :delai_revise,
                statut = COALESCE(:statut, statut),
                date_cloture = CURRENT_DATE
            WHERE plan_id = :plan_id
            """
        else:
            update_query = """
            UPDATE public.plan_action
            SET commentaire = :commentaire,
                delai_revise = :delai_revise,
                statut = COALESCE(:statut, statut),
                date_cloture = NULL
            WHERE plan_id = :plan_id
            """

        with engine.begin() as conn:
            result = conn.execute(text(update_query), {
                "plan_id": plan_id,
                "commentaire": commentaire,
                "delai_revise": delai_revise,
                "statut": statut
            })

        if result.rowcount == 0:
            return False, f"Aucun plan d'action trouvé avec plan_id={plan_id}"

        return True, "Plan d'action mis à jour avec succès"

    except Exception as e:
        return False, str(e)

def get_all_plan_actions(engine, filter_date_cloture_null=True):
    base_query = """
        SELECT
            p.plan_id,
            p.personnel_id,
            pers."Nom",
            pers."Prenom",
            p.type,
            p.action,
            p.sujet,
            p.date,
            p.statut,
            p.commentaire,
            p.delai_initiale,
            p.delai_revise,
            p.date_cloture
        FROM public.plan_action p
        LEFT JOIN public."Personnel" pers ON pers."Personnel_Id" = p.personnel_id
    """

    if filter_date_cloture_null:
        base_query += " WHERE p.date_cloture IS NULL"
    else:
        base_query += " WHERE p.date_cloture IS NOT NULL"

    base_query += " ORDER BY p.date DESC NULLS LAST"

    query = text(base_query)

    df = pd.read_sql(query, engine)
    for col in ['date', 'delai_initiale', 'delai_revise', 'date_cloture']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)
    df['pilote_nom'] = df['Nom'] + ' ' + df['Prenom']
    return df.to_dict(orient='records')


def get_plan_actions_for_personnel(engine, personnel_id):
    """
    Récupère tous les plans d'action liés à un personnel donné, triés par date décroissante.
    """
    query = text("""
        SELECT plan_id, personnel_id, type, action, sujet, date, statut, commentaire, delai_initiale, delai_revise
        FROM public.plan_action
        WHERE personnel_id = :personnel_id
        ORDER BY date DESC NULLS LAST
    """)
    df = pd.read_sql(query, engine, params={"personnel_id": personnel_id})
    if df.empty:
        return []
    # Convertir dates en chaînes ISO pour JSON
    for col in ['date', 'delai_initiale', 'delai_revise']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)
    return df.to_dict(orient='records')

def delete_plan_action(engine, plan_id):
    """
    Supprime un plan d'action par son plan_id.
    Renvoie (success: bool, message: str)
    """
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM public.plan_action WHERE plan_id = :plan_id"),
                {"plan_id": plan_id}
            )
        if result.rowcount == 0:
            return False, "Plan d'action non trouvé"
        return True, "Plan d'action supprimé"
    except Exception as e:
        return False, str(e)
