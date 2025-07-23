import os
import logging
import random
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

from openai import OpenAI
from dotenv import load_dotenv
import mail as MailSMTP

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()


messages = []
MODEL = "gpt-4o-mini"

email_actions = ["gere um email", "criar um email", "escreva um email", "faça um email", 'faz um email', 'monte uma email', 'elabore uma email', 'redija um email']
email_responses = ["Já enviei", "Email enviado", "Já tá feito", 'Acabei de mandar', 'Envio realizado', 'Já está na caixa de enviados']




def client_gpt() -> OpenAI:
    openai_api_key = os.getenv('KEY_GPT')
    client = OpenAI(api_key=openai_api_key)
    return client


# Instruções para o sistema
def system_instructions():
    instruction = """
        Você é um assistente pessoal de nome Altair. 
        Responda de forma, direta e curta. 
        Responda em Português do Brasil.
        Não tente explicar sua resposta.
        Não repita a pergunta feita.
    """
    return { "role": "system", "content": instruction, }


# encontrar categoria
def categorize(question: str):
    response = client_gpt().chat.completions.create(model=MODEL, messages=[{"role": "assistant", "content": question}], temperature=0.5, stream=False)
    return response.choices[0].message.content


# Fazer a pergunta
def to_ask(question: str):
    messages.append({"role": "user", "content": question})
    response = client_gpt().chat.completions.create(model=MODEL, messages=messages, temperature=0.8, stream=False)
    return response.choices[0].message.content


def discover_the_intention(question: str):
    actions = "" 
    for action in email_actions:
        actions += f"- {action}\n        "
        
    prompt = f"""
        /shorten
        Verifique a intenção para ação da pergunta abaixo.
        Responda somente com a ação encontrada em uma das opções.
        Caso não encontrar uma opção, responda com texto vazio.
        As opções de categorias são:
        {actions}
        Com base na seguinte pergunta, categorize: {question}
    """
    response = categorize(prompt)
    return response


def extract_email_addressee(question: str):
    addressee_email = "lucasfrct@gmail.com"
    
    prompt = f"""
        /shorten
        Descubra o endereço do email do destinatário expresso no texto.
        O endereço de email deve conter um dominio com @.
        O endereço de email deve ser diferente de {addressee_email}.
        O email pode estar perto do trecho 'envie para...', 'enviar para...', 'mandar para...'
        Encontre o endereço de email do destinatário no seguinte texto: {question}
        Se não encontrar o endereço de email, retorne {addressee_email}.
        Retorne somente o endereço de email do destinatário.
    """
    return to_ask(prompt)


def extract_email_sender(question: str):
    sender_email = "lucasfrct@gmail.com"
    
    prompt = f"""
        /shorten
        Descarte o email de destinatário expresso no texto.
        Descubra o email do remetente expresso no texto.
        Se não encontrar o email do remetente, retorne {sender_email}.
        Encontre o email do remetente no seguinte texto: {question}
        Retorne somente o email do remetente.
    """
    return to_ask(prompt)


def extract_name_addressee(question: str):
    addressee_name = "Lucas Costa"
    
    prompt = f"""
        /shorten
        Extraia o nome do destinatário.
        retorne somente o nome do destinatário.
        Encontre o nome formal do receptor do email.
        Se não encontrar o nome, retorne {addressee_name}.
        Responda com o nome que indique ser o destinatário : {question}
    """
    return to_ask(prompt)


def extract_name_sender(question: str):
    sender_name = "Lucas Costa"
    prompt = f"""
        /shorten
        Extraia o nome do remetente.
        Retorne somente o nome do emissor.
        Encontre o nome formal do emissor do email.
        Se não encontrar o nome, retorne {sender_name}.
        Responda com o nome que indique ser o emissário: {question}
    """
    return to_ask(prompt)


def assign_title(email: str):
    prompt = f"""
        /shorten
        Atribua um título para o email abaixo com no máximo 5 palavras.
        O título deve expressar a intenção principal do email.
        Não responda com a pergunta.
        Se não houver título, retorne vazio.
        Responda com o título para o email: {email}
    """
    return to_ask(prompt)


def action_email(question: str):
    addressee_email = extract_email_addressee(question)
    if addressee_email == "":
        return "Não foi possível identificar o destinatário."
    
    addressee_name = extract_name_addressee(question)
  
    sender_email = extract_email_sender(question)
    if sender_email == "":
        return "Não foi possível identificar o remetente."

    sender_name = extract_name_sender(question)
    
    title = assign_title(question)
    if title == "":
        return "Não foi possível identificar o título do email."
    
    instructions = f"""
        /context
        Use uma linguagem formal e pessoal.
        Seja educado e empático.
        Remova o texto 'Assunto:'.
        Deve conter uma saudação.
        Não use abreviações.
        Não use gírias.
        Deve conter uma despedida cordial.
        
        /shorten
        O email destinatário é: {addressee_email}
        O Nome destinatário é: {addressee_name}
        O email do remetente é: {sender_email}
        O Nome do remetente é: {sender_name}
        {question}
    """
    
    email = to_ask(instructions)
    try:
        MailSMTP.send_email(sender_email, addressee_email, title, email)
        return f"{random.choice(email_responses)} de {sender_email} para {addressee_email}"
    except Exception as e:
        return f"Email criado, mas não pude enviar: {str(e)}"


def generate_gpt_response(query):
    try:
        actions = ""
        for action in email_actions:
            actions += f"- {action}\n"
            
        intention = discover_the_intention(query).strip()
        
        if intention != "" and intention in actions:
            return action_email(query)
        
        messages.append(
            {"role": "user", "content": query},
        )
        response = client_gpt().chat.completions.create(
            model=MODEL, messages=messages, max_tokens=700, temperature=0.8
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}"
        
    
class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = ("Oi!")

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class GptQueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("GptQueryIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        query = handler_input.request_envelope.request.intent.slots["query"].value
        response = generate_gpt_response(query)

        return (
            handler_input.response_builder.speak(response)
            .ask("Você pode fazer uma nova pergunta: sair.")
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Diga?"

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.CancelIntent")(
            handler_input
        ) or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Até mais!"

        return handler_input.response_builder.speak(speak_output).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Desculpe, não posso te entender."

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


messages.append(system_instructions())

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GptQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()