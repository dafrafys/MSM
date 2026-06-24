# app/services/notes.py

from sqlalchemy import text

def ajouter_note(engine, session_id, type_note, information):
    """
    Ajoute des notes à la session rattaché à la zone (qualité/ sécurité...) .
    Lève une exception en cas d'erreur.
    """
    insert_query = text('''
        INSERT INTO public."Huddle_notes" ("Session_Id", "Type_note", "Information")
        VALUES (:Session_Id, :Type_note, :Information)
    ''')
    with engine.begin() as conn:
        conn.execute(insert_query, {
            "Session_Id": session_id,
            "Type_note": type_note,
            "Information": information
        })
    return True
