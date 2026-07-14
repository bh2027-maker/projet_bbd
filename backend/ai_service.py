"""Service d'analyse IA via Claude Sonnet 4.5 (clé Emergent universelle)."""
import os
from emergentintegrations.llm.chat import LlmChat, UserMessage


async def generate_commune_comment(commune: dict) -> str:
    """
    Génère un commentaire IA (2-3 phrases) expliquant pourquoi cette commune
    est prioritaire (ou non) pour la prospection pompe à chaleur.
    """
    api_key = os.environ["EMERGENT_LLM_KEY"]

    system = (
        "Tu es un analyste commercial senior spécialisé en prospection terrain "
        "pour la vente de pompes à chaleur air-eau (BAR-TH-171) en France. "
        "Tu produis des synthèses courtes, directes, opérationnelles, "
        "destinées à un commercial qui va se déplacer sur le terrain. "
        "Pas de blabla marketing. Style factuel, chiffres à l'appui. "
        "Réponds toujours en français, en 2 à 3 phrases maximum."
    )

    prompt = (
        f"Commune analysée : {commune['nom']} ({commune['code_postal']}, "
        f"département {commune['departement']}, Massif des Bauges).\n"
        f"- Population : {commune['population']} hab.\n"
        f"- Logements : {commune['nb_logements']} dont ~{commune['nb_maisons_individuelles']} "
        f"maisons individuelles ({commune['part_maisons_pct']}%)\n"
        f"- Parc construit avant 2000 : {commune['part_logements_avant_2000_pct']}%\n"
        f"- Revenu médian : {commune['revenu_median']} € / an\n"
        f"- Altitude : {commune['altitude_m']} m (zone climatique H1)\n"
        f"- Score BBD calculé : {commune['score_bbd']}/100\n"
        f"- Dossiers BAR-TH-171 estimés : {commune['dossiers_bar_th_171_estimes']}\n\n"
        "Explique en 2-3 phrases pourquoi cette commune est intéressante ou pas "
        "pour une tournée commerciale pompe à chaleur, en pointant le levier principal "
        "(ancienneté, revenu, volume, climat) et un point d'attention."
    )

    chat = LlmChat(
        api_key=api_key,
        session_id=f"bbd-commune-{commune['code_insee']}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    response = await chat.send_message(UserMessage(text=prompt))
    return response.strip() if isinstance(response, str) else str(response).strip()
