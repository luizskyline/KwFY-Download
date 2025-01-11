import requests
import yt_dlp
import re
import os


# Função para normalizar strings (remover caracteres inválidos)
def normalize_str(normalize_me):
    return " ".join(re.sub(r'[<>:!"/\\|?*]', '', normalize_me)
                    .replace('\t', '')
                    .replace('\n', '')
                    .replace('.', '')
                    .split(' ')).strip()


# Definir o domínio base para os links de vídeo (caso necessário)
BASE_URL = "https://d3pjuhbfoxhm7c.cloudfront.net"

# Iniciar sessão e configurar cabeçalhos
sesh = requests.session()
sesh.headers[
    'user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'

# Solicitar e obter dados de login
user_email = input('Seu email da Kwfy: ')
user_pass = input('Sua senha da Kwfy: ')

post_me = {
    'email': user_email,
    'password': user_pass,
    'returnSecureToken': True
}

# Autenticar e obter o token de acesso
auth_dict = sesh.post(
    "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=AIzaSyDmOO1YAGt0X35zykOMTlolvsoBkefLKFU",
    data=post_me).json()

# Se não houver idToken, algo deu errado
if 'idToken' not in auth_dict:
    print("Falha na autenticação. Verifique suas credenciais.")
    exit()

# Definir token de autenticação
sesh.headers['authorization'] = f"Bearer {auth_dict['idToken']}"

# Obter cursos disponíveis
account_courses = sesh.get("https://api.kiwify.com.br/v1/viewer/courses?&page=1").json()
total_courses = account_courses['count']
courses_fetched = 10
courses = account_courses['courses']
page_count = 1
print(f"Cursos disponíveis na conta: {total_courses}")

# Pegar todos os cursos
while courses_fetched < total_courses:
    account_courses = sesh.get(f"https://api.kiwify.com.br/v1/viewer/courses?&page={page_count}").json()
    page_count += 1
    courses_fetched += 10
    courses.extend(account_courses['courses'])

# Exibir os cursos
for idx, course in enumerate(courses, start=1):
    print(
        f"\t{idx}. {course['name']} - {course['store']['custom_name']}({course['producer']['name']}) prog:{course['completed_progress']}%")

# Solicitar o curso a ser baixado
chosen_course = int(input("Curso para baixar: ")) - 1
dl_course = courses[chosen_course]

# Informações do curso
infos = sesh.get(f"https://api.kiwify.com.br/v1/viewer/courses/{dl_course['id']}").json()


# Função para baixar o vídeo de uma lição
def download_video(lesson, lesson_path):
    video_url = None
    # Checar se há vídeo (M3U8)
    if lesson.get('video'):
        video_url = lesson['video'].get('stream_link') or lesson['video'].get('download_link')

    # Se o link for relativo, completar com o BASE_URL
    if video_url and video_url.startswith("/"):
        video_url = BASE_URL + video_url

    # Se encontrou um link de vídeo válido, proceder com o download
    if video_url:
        print(f"Tentando baixar vídeo da URL: {video_url}")

        # Definir opções para o yt-dlp (usando a URL M3U8 fornecida)
        ydl_opts = {
            'format': 'best',  # Baixar a melhor qualidade
            'outtmpl': f"{lesson_path}/%(title)s.%(ext)s",  # Salvar com nome da lição
            'noplaylist': True,  # Não baixar a playlist inteira, apenas o vídeo
            'quiet': False,  # Não usar quiet, para ver detalhes de download
            'merge_output_format': 'mp4',  # Formato de saída
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])  # Baixar o vídeo a partir da URL M3U8
        except Exception as e:
            print(f"Erro ao tentar baixar o vídeo: {e}")
    else:
        print(f"Nenhum link de vídeo encontrado para a lição: {lesson['title']}")


# Baixar todos os vídeos do curso
for module in infos['course']['modules']:
    print(f"Baixando módulo: {module['order']}. {normalize_str(module['name'])}")
    for lesson in module.get('lessons', []):
        print(f"\tBaixando lição: {lesson['order']}. {normalize_str(lesson['title'])}")

        # Verificar se a aula não está expirada ou bloqueada
        if lesson.get('expired') or lesson.get('locked'):
            print("\tAula expirada ou bloqueada!")
            continue

        # Criar caminho para salvar os arquivos
        lesson_path = f"{normalize_str(dl_course['name'])}/{module['order']}. {normalize_str(module['name'])}/{lesson['order']}. {normalize_str(lesson['title'])}"
        if not os.path.exists(lesson_path):
            os.makedirs(lesson_path)

        # Baixar conteúdo adicional (se houver)
        if lesson.get('content'):
            with open(f"{lesson_path}/descrição.html", "w", encoding="utf-8") as desc:
                desc.write(lesson['content'])

        # Baixar materiais (arquivos)
        if lesson.get('files'):
            if not os.path.exists(f"{lesson_path}/Materiais"):
                os.makedirs(f"{lesson_path}/Materiais")
            for att in lesson['files']:
                print(f"\t\t\tBaixando o anexo: {att['name']}")
                if not os.path.isfile(f"{lesson_path}/Materiais/{att['name']}"):
                    file_data = requests.get(att['url'], headers={'User-Agent': 'Mozilla/5.0'})
                    with open(f"{lesson_path}/Materiais/{att['name']}", "wb") as att_file:
                        att_file.write(file_data.content)
                else:
                    print("\t\t\tAnexo já presente!")

        # Baixar vídeo
        download_video(lesson, lesson_path)
