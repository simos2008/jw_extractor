import streamlit as st
import zipfile
import sqlite3
import os
import uuid
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="JW to BTNotes XML", page_icon="📚", layout="centered")

st.title("📚 Διαγνωστικός Μετατροπέας JW Library")
st.write("Ανεβάστε το αρχείο σας για να δούμε όλες τις σημειώσεις που περιέχει η βάση δεδομένων σας.")

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
            
            # 1. Διαγνωστικό βήμα: Παίρνουμε ΟΛΕΣ τις σημειώσεις χωρίς κανένα φίλτρο
            try:
                cursor.execute("SELECT Title, Content, Created FROM Note;")
                rows = cursor.fetchall()
            except Exception as e:
                st.error(f"Σφάλμα κατά την ανάγνωση του πίνακα Note: {e}")
                rows = []
                
            conn.close()
            
            if rows:
                st.success(f"📊 Συνολικά βρέθηκαν {len(rows)} σημειώσεις στη βάση δεδομένων σας!")
                st.write("Παρακάτω φαίνονται οι πρώτες 10 σημειώσεις για να καταλάβουμε τη δομή τους:")
                
                # Εμφάνιση των πρώτων 10 σημειώσεων για έλεγχο
                for idx, row in enumerate(rows[:10], start=1):
                    st.markdown(f"**{idx}. Τίτλος:** {row[0]} | **Ημερομηνία:** {row[2]}")
                    st.write(f"*{row[1]}*")
                    st.markdown("---")
                
                # 2. Δημιουργία XML με ΟΛΕΣ τις σημειώσεις για να κάνεις τη δουλειά σου άμεσα
                root_xml = ET.Element("db", serverCounter=str(len(rows) + 50))
                folders_element = ET.SubElement(root_xml, "folders")
                import_folder_uuid = str(uuid.uuid4())
                
                ET.SubElement(folders_element, "folder", {
                    "id": "1001",
                    "uuid": import_folder_uuid,
                    "name": "Όλες οι σημειώσεις JW",
                    "parent": "null",
                    "password": "null"
                })
                
                talks_element = ET.SubElement(root_xml, "talks", number=str(len(rows)))
                current_timestamp = str(int(time.time() * 1000))
                
                for idx, row in enumerate(rows, start=1):
                    title_text, content_text, created_date = row
                    
                    final_title = str(title_text) if title_text and str(title_text).strip() != "None" else f"Σημείωση {idx}"
                    final_content = str(content_text) if content_text else ""
                    
                    talk_uuid = str(uuid.uuid4())
                    talk_node = ET.SubElement(talks_element, "talk", {
                        "id": str(idx + 100),
                        "uuid": talk_uuid,
                        "last_created": "1",
                        "lang": "64",
                        "date": current_timestamp,
                        "last_open": current_timestamp,
                        "folder": import_folder_uuid
                    })
                    
                    title = ET.SubElement(talk_node, "title")
                    title.text = final_title
                    
                    speaker = ET.SubElement(talk_node, "speaker")
                    speaker.text = "JW Library"
                    
                    paragrafs = ET.SubElement(talk_node, "paragrafs")
                    paragraf = ET.SubElement(paragrafs, "paragraf", {
                        "id": str(idx + 5000),
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
                
                xml_filename = "jw_all_notes_import.xml"
                with open(xml_filename, "wb") as f:
                    f.write(pretty_xml)
                
                st.success("Δημιουργήθηκε αρχείο XML με ΟΛΕΣ τις σημειώσεις σας!")
                with open(xml_filename, "rb") as f:
                    st.download_button(
                        label="📥 Κατεβάστε το αρχείο .xml με ΟΛΕΣ τις σημειώσεις",
                        data=f,
                        file_name="jw_all_notes.xml",
                        mime="application/xml"
                    )
            else:
                st.warning("Δεν βρέθηκε απολύτως καμία σημείωση μέσα στον πίνακα Note της βάσης δεδομένων.")
        else:
            st.error("Δεν βρέθηκε αρχείο βάσης δεδομένων.")
            
    except Exception as e:
        st.error(f"Σφάλμα κατά την επεξεργασία: {e}")
        
