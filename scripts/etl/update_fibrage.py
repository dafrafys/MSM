def update_fibrage_source(src_path=None, dst_dir=None):
    """
    Essaie de copier le fichier source (réseau) vers data/.
    Si le chemin source est inaccessible, ne fait rien ou log l’erreur.
    Retourne le chemin local (data/…) pour que extract puisse lire.
    """
    # ...déterminer src_path, dst_dir, filename...
    try:
        shutil.copy2(src_path, dst_path)  # met à jour la copie locale
        print("Copie réussie vers", dst_path)
    except Exception as e:
        print("Erreur lors de la copie :", e)
        # On peut choisir ici de raise ou juste d'utiliser le fichier local s'il existe déjà
    return dst_path  # on retourne toujours le chemin local
