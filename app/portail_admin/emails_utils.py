import logging
from flask_mail import Message
from app import mail

logger = logging.getLogger(__name__)

def send_flight_cancellation_email(user_email, prenom, nom, pnr, app):
    """
    Envoie un email pour notifier le client de l'annulation de son vol et de sa réservation.
    
    Args:
        user_email (str): Email de l'utilisateur
        prenom (str): Prénom du client
        nom (str): Nom du client
        pnr (str): Numéro de réservation (PNR)
        app: Instance de l'application Flask
    
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    try:
        with app.app_context():
            msg = Message(
                subject=f"Important : Annulation de votre vol O'Buffair (Réservation {pnr})",
                recipients=[user_email],
                html=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #d9534f;">Annulation de votre réservation</h2>
                            
                            <p>Bonjour {prenom} {nom},</p>
                            
                            <p>Nous vous informons avec regret que le vol associé à votre réservation <strong>{pnr}</strong> a été annulé par notre compagnie pour des raisons opérationnelles.</p>
                            
                            <p>Par conséquent, l'intégralité de votre réservation a été annulée. Un remboursement complet sera automatiquement effectué sur le moyen de paiement utilisé lors de l'achat dans les prochains jours.</p>
                            
                            <p>Nous vous présentons nos plus sincères excuses pour la gêne occasionnée.</p>
                            
                            <p style="color: #666; margin-top: 30px;">
                                L'équipe O'Buffair reste à votre entière disposition pour toute question.
                            </p>
                            
                            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                            
                            <p style="color: #999; font-size: 11px; text-align: center;">
                                © Obuffair - Tous droits réservés
                            </p>
                        </div>
                    </body>
                </html>
                """
            )
            
            mail.send(msg)
            logger.info(f'Email d\'annulation envoyé à: {user_email} pour la réservation {pnr}')
            return True
            
    except Exception as e:
        logger.error(f'Erreur lors de l\'envoi d\'email d\'annulation à {user_email}: {str(e)}')
        return False