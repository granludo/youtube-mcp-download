import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

def main():
    # Cargar variables de entorno desde el archivo .env
    load_dotenv()
    
    # Obtener la API key del entorno
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: La variable de entorno OPENAI_API_KEY no está configurada.")
        print("Por favor, configura tu API key de OpenAI:")
        print("set OPENAI_API_KEY=tu_api_key_aqui")
        sys.exit(1)
    
    # Crear el cliente de OpenAI con la API key
    client = OpenAI(api_key=api_key)
    
    # Pedir al usuario el path del archivo
    file_path = input("Ingresa el path del archivo de video/audio a transcribir: ").strip()
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        print(f"Error: El archivo '{file_path}' no existe.")
        sys.exit(1)
    
    # Verificar que es un archivo
    if not os.path.isfile(file_path):
        print(f"Error: '{file_path}' no es un archivo válido.")
        sys.exit(1)
    
    print(f"Transcribiendo archivo: {file_path}")
    
    try:
        # Abrir el archivo de audio/video
        with open(file_path, "rb") as audio_file:
            # Crear la transcripción
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",  # Usar el modelo correcto de Whisper
                file=audio_file
            )
        
        print("\n--- TRANSCRIPCIÓN ---")
        print(transcription.text)
        
        # Opcionalmente guardar la transcripción en un archivo
        save_option = input("\n¿Deseas guardar la transcripción en un archivo? (s/n): ").strip().lower()
        if save_option in ['s', 'sí', 'si', 'yes', 'y']:
            output_file = Path(file_path).stem + "_transcripcion.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(transcription.text)
            print(f"Transcripción guardada en: {output_file}")
    
    except Exception as e:
        print(f"Error durante la transcripción: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()