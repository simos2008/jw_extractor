import streamlit as st
import zipfile
import sqlite3
import os
import uuid
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="JW to BTNotes Perfect", page_icon="📚", layout="centered")

st.title("📚 Οργανωμένος Μετατροπέας JW Library (Έκδοση με Εδάφια)")
st.write("Αυτό το εργαλείο βρίσκει τα κρυμμένα εδάφια από το JW Library και τα βάζει στον τίτλο κάθε σημείωσης.")

BIBLE_BOOKS = {
    1: "Γένεση", 2: "Έξοδος", 3: "Λευιτικό", 4: "Αριθμοί", 5: "Δευτερονόμιο",
    6: "Ιησούς του Ναυή", 7: "Κριτές", 8: "Ρουθ", 9: "Α΄ Σαμουήλ", 10: "Β΄ Σαμουήλ",
    11: "Α΄ Βασιλέων", 12: "Β΄ Βασιλέων", 13: "Α΄ Χρονικών", 14: "Β΄ Χρονικών",
    15: "Έσδρας", 16: "Νεεμίας", 17: "Εσθήρ", 18: "Ιώβ", 19: "Ψαλμοί",
    20: "Παροιμίες", 21: "Εκκλησιαστής", 22: "Άσμα Ασμάτων", 23: "Ησαΐας",
    24: "Ιερεμίας", 25: "Θρήνοι", 26: "Ιεζεκιήλ", 27: "Δανιήλ", 28: "Ωσηέ",
    29: "Ιωήλ", 30: "Αμώς", 31: "Αβδιού", 32: "Ιωνάς", 33: "Μιχαίας",
    34: "Ναούμ", 35: "Αββακούμ", 36: "Σοφονίας", 37: "Αγγαίος", 38: "Ζαχαρίας",
    39: "Μαλαχίας", 40: "Κατά Ματθαίον", 41: "Κατά Μάρκον", 42: "Κατά Λουκάν",
    43: "Κατά Ιωάννην", 44: "Πράξεις", 45: "Ρωμαίους", 46: "Α΄ Κορινθίους",
    47: "Β΄ Κορινθίους", 48: "Γαλάτες", 49: "Εφεσίους", 50: "Φιλιππησίους",
    51: "Κολοσσαείς", 52: "Α΄ Θεσσαλονικείς", 53: "Β΄ Θεσσαλονικείς",
    54: "Α΄ Τιμόθεο", 55: "Β΄ Τιμόθεο", 56: "Τίτο", 57: "Φιλήμονα",
    58: "Εβραίους", 59: "Ιακώβου", 60: "Α΄ Πέτρου", 61: "Β΄ Πέτρου",
    62: "Α΄ Ιωάννη", 63: "Β΄ Ιωάννη", 64: "Γ΄ Ιωάννη", 65: "Ιούδα",
    66: "Αποκάλυψη"
}

uploaded_file = st.file_uploader("Ανεβάστε το αρχείο .jwlibrary", type=["jwlibrary"])

if uploaded_file is not None:
    target_dir = "temp_extracted"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    with open("temp_backup.zip", "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        with zipfile.ZipFile("temp_backup.zip", "r") as zip_ref:
            zip_ref.extractall(target_dir)
            
        db_path = None
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith('.db'):
                    db_path = os.path.join(root, file)
                    break
        
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Διάγνωση στηλών του πίνακα Location για να δούμε αν λέγεται Verse ή VerseNumber
            cursor.execute("PRAGMA table_info(Location);")
            columns = [col[1] for col in cursor.fetchall()]
            v_col = "Verse" if "Verse" in columns else ("VerseNumber" if "VerseNumber" in columns else "null")
            
            # Ερώτημα που ενώνει τη σημείωση (Note) με την τοποθεσία (Location)
            # Χρησιμοποιούμε σωστά το Note.LocationId = Location.LocationId
            query = f"""
                SELECT 
                    L.BookNumber, 
                    L.ChapterNumber, 
                    L.IssueTagNumber,
                    {f'L.{v_col}' if v_col != 'null' else '1'},
                    N.Title, 
                    N.Content
                FROM Note N
                LEFT JOIN Location L ON N.LocationId = L.LocationId;
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                root_xml = ET.Element("db", serverCounter=str(len(rows) + 500))
                folders_element = ET.SubElement(root_xml, "folders")
                
                # Κεντρικός Φάκελος
                main_folder_uuid = str(uuid.uuid4())
                ET.SubElement(folders_element, "folder", {
                    "id": "1001",
                    "uuid": main_folder_uuid,
                    "name": "Σημειώσεις JW Library",
                    "parent": "null",
                    "password": "null"
                })
                
                book_folders = {}
                book_folder_id_counter = 2000
                
                talks_element = ET.SubElement(root_xml, "talks", number=str(len(rows)))
                current_timestamp = str(int(time.time() * 1000))
                
                for idx, row in enumerate(rows, start=1):
                    book_num, chapter, issue_tag, verse, title_text, content_text = row
                    
                    # Έλεγχος αν είναι βιβλίο της Γραφής
                    if book_num and book_num in BIBLE_BOOKS:
                        book_name = BIBLE_BOOKS[book_num]
                        
                        # Δημιουργία υποφακέλου για το βιβλίο αν δεν υπάρχει
                        if book_name not in book_folders:
                            sub_folder_uuid = str(uuid.uuid4())
                            book_folders[book_name] = sub_folder_uuid
                            ET.SubElement(folders_element, "folder", {
                                "id": str(book_folder_id_counter),
                                "uuid": sub_folder_uuid,
                                "name": book_name,
                                "parent": main_folder_uuid,
                                "password": "null"
                            })
                            book_folder_id_counter += 1
                        
                        target_folder_uuid = book_folders[book_name]
                        
                        # Φτιάχνουμε το σωστό εδάφιο [Ψαλμοί 119:105]
                        ch_part = f" {chapter}" if chapter else ""
                        v_part = f":{verse}" if verse and str(verse) != "0" else ""
                        prefix = f"[{book_name}{ch_part}{v_part}] "
                    else:
                        target_folder_uuid = main_folder_uuid
                        prefix = "[Γενική Σημείωση] "
                    
                    # Καθαρισμός τίτλου
                    user_title = str(title_text).strip() if title_text and str(title_text).strip() != "None" else ""
                    
                    # Φτιάχνουμε τον τελικό τίτλο: Εδάφιο + ο Τίτλος σου (αν υπάρχει)
                    if user_title:
                        final_title = prefix + user_title
                    else:
                        # Αν δεν είχες βάλει τίτλο, παίρνουμε τις πρώτες 4 λέξεις από το κείμενο για να φαίνεται όμορφο
                        clean_content = str(content_text).strip() if content_text else ""
                        words = clean_content.split()
                        preview = " ".join(words[:4]) + "..." if len(words) > 4 else clean_content
                        final_title = prefix + (preview if preview else "Σημείωση")
                        
                    final_content = str(content_text) if content_text else ""
                    
                    talk_uuid = str(uuid.uuid4())
                    talk_node = ET.SubElement(talks_element, "talk", {
                        "id": str(idx + 10000),
                        "uuid": talk_uuid,
                        "last_created": "1",
                        "lang": "64",
                        "date": current_timestamp,
                        "last_open": current_timestamp,
                        "folder": target_folder_uuid
                    })
                    
                    title = ET.SubElement(talk_node, "title")
                    title.text = final_title
                    
                    speaker = ET.SubElement(talk_node, "speaker")
                    speaker.text = "JW Library"
                    
                    paragrafs = ET.SubElement(talk_node, "paragrafs")
                    paragraf = ET.SubElement(paragrafs, "paragraf", {
                        "id": str(idx + 50000),
                        "orden": "0",
                        "indent": "1",
                        "color": "-1",
                        "created": current_timestamp
                    })
                    
                    text = ET.SubElement(paragraf, "text")
                    text.text = final_content
                    ET.SubElement(paragraf, "verses")
                
                xml_str = ET.tostring(root_xml, encoding='utf-8')
                parsed_xml = minidom.parseString(xml_str)
                pretty_xml = parsed_xml.toprettyxml(indent="    ", encoding="utf-8")
                
                xml_filename = "jw_perfect_import.xml"
                with open(xml_filename, "wb") as f:
                    f.write(pretty_xml)
                
                st.markdown("---")
                st.success(f"🎉 Επιτυχία! Ετοιμάστηκε το αρχείο με {len(rows)} οργανωμένες σημειώσεις!")
                
                with open(xml_filename, "rb") as f:
                    st.download_button(
                        label="📥 Κατεβάστε το ΤΕΛΙΚΟ αρχείο .xml",
                        data=f,
                        file_name="jw_perfect_import.xml",
                        mime="application/xml"
                    )
            else:
                st.warning("Δεν βρέθηκαν σημειώσεις.")
        else:
            st.error("Δεν βρέθηκε αρχείο βάσης δεδομένων.")
            
    except Exception as e:
        st.error(f"Σφάλμα κατά την επεξεργασία: {e}")
        
