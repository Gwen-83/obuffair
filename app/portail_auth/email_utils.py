"""
Utilitaires pour l'envoi d'emails.
Gère l'envoi des emails de réinitialisation de mot de passe.
"""

import logging
from flask_mail import Message
from app import mail

logger = logging.getLogger(__name__)


def send_verification_email(user_email, verification_token, app):
    """
    Envoie un email de vérification d'email à l'utilisateur.
    
    Args:
        user_email (str): Email de l'utilisateur
        verification_token (str): Token de vérification unique
        app: Instance de l'application Flask
    
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    try:
        with app.app_context():
            # Construire le lien de vérification
            server_url = app.config.get('SERVER_URL', 'http://localhost:5000')
            verify_link = f"{server_url}/auth/verify-email/{verification_token}"
            
            # Créer le message
            msg = Message(
                subject='Vérifiez votre email - Obuffair',
                recipients=[user_email],
                html=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #0066cc;">Bienvenue sur Obuffair!</h2>
                            
                            <p>Bonjour,</p>
                            
                            <p>Merci de vous être inscrit sur Obuffair. Pour activer votre compte, veuillez vérifier votre adresse email.</p>
                            
                            <p>Cliquez sur le lien ci-dessous pour confirmer votre email:</p>
                            
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{verify_link}" 
                                   style="background-color: #0066cc; color: white; padding: 12px 30px; 
                                           text-decoration: none; border-radius: 5px; display: inline-block;">
                                    Vérifier mon email
                                </a>
                            </div>
                            
                            <p style="color: #666; font-size: 12px;">
                                Ou copiez et collez ce lien dans votre navigateur:<br>
                                <code style="background-color: #f5f5f5; padding: 10px; display: block; margin-top: 10px; word-break: break-all;">
                                    {verify_link}
                                </code>
                            </p>
                            
                            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                                Ce lien expire dans 24 heures pour des raisons de sécurité.
                            </p>
                            
                            <p style="color: #999; font-size: 12px;">
                                Si vous n'avez pas créé ce compte, ignorez cet email.
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
            
            # Envoyer l'email
            mail.send(msg)
            logger.info(f'Email de vérification envoyé à: {user_email}')
            return True
            
    except Exception as e:
        logger.error(f'Erreur lors de l\'envoi d\'email à {user_email}: {str(e)}')
        return False


def send_reset_password_email(user_email, reset_token, app):
    """
    Envoie un email de réinitialisation de mot de passe à l'utilisateur.
    
    Args:
        user_email (str): Email de l'utilisateur
        reset_token (str): Token de réinitialisation unique
        app: Instance de l'application Flask
    
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    try:
        with app.app_context():
            # Construire le lien de réinitialisation
            server_url = app.config.get('SERVER_URL', 'http://localhost:5000')
            reset_link = f"{server_url}/auth/reset-password/{reset_token}"
            
            # Créer le message
            msg = Message(
                subject='Réinitialisation de votre mot de passe Obuffair',
                recipients=[user_email],
                html=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #0066cc;">Réinitialisation de votre mot de passe</h2>
                            
                            <p>Bonjour,</p>
                            
                            <p>Vous avez demandé la réinitialisation de votre mot de passe pour votre compte Obuffair.</p>
                            
                            <p>Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe:</p>
                            
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{reset_link}" 
                                   style="background-color: #0066cc; color: white; padding: 12px 30px; 
                                           text-decoration: none; border-radius: 5px; display: inline-block;">
                                    Réinitialiser mon mot de passe
                                </a>
                            </div>
                            
                            <p style="color: #666; font-size: 12px;">
                                Ou copiez et collez ce lien dans votre navigateur:<br>
                                <code style="background-color: #f5f5f5; padding: 10px; display: block; margin-top: 10px; word-break: break-all;">
                                    {reset_link}
                                </code>
                            </p>
                            
                            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                                Ce lien expire dans 1 heure pour des raisons de sécurité.
                            </p>
                            
                            <p style="color: #999; font-size: 12px;">
                                Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
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
            
            # Envoyer l'email
            mail.send(msg)
            logger.info(f'Email de réinitialisation envoyé à: {user_email}')
            return True
            
    except Exception as e:
        logger.error(f'Erreur lors de l\'envoi d\'email à {user_email}: {str(e)}')
        return False
