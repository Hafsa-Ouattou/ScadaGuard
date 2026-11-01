from auth import creer_utilisateur

creer_utilisateur("admin", "Admin@ONEE2026", role="admin")
print("Comptes créés avec succès dans users.json :")
print(" - admin / Admin@ONEE2026  (rôle : admin, accès complet + export)")
print("\nPense à changer ces mots de passe avant toute utilisation réelle.")
