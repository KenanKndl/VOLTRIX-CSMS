"""
Otomata yükleyici modülü.

Bu modül, XML dosyalarından otomata tanımlarını yükleyen ve 
işleyen sınıfları içerir.
"""

import os
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class AutomataLoader:
    """XML dosyalarından otomata tanımlarını yükleyen sınıf."""
    
    def __init__(self, base_dir: str = None):
        """
        AutomataLoader sınıfını başlatır.
        
        Args:
            base_dir: Otomata XML dosyalarının bulunduğu ana dizin.
                      None ise, server/automata klasörü kullanılır.
        """
        if base_dir is None:
            # Otomata dosyalarının varsayılan konumu
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.base_dir = current_dir
        else:
            self.base_dir = base_dir
            
        self.dfa_dir = os.path.join(self.base_dir, "dfa")
        self.nfa_dir = os.path.join(self.base_dir, "nfa")
        
        # Yüklenen otomatalar için depolama
        self.loaded_automata = {}
        
    def load_all_automata(self) -> Dict[str, Any]:
        """
        Tüm DFA ve NFA otomatalarını yükler.
        
        Returns:
            Yüklenen tüm otomataların bir sözlüğü.
        """
        # DFA'ları yükle
        self._load_automata_from_dir(self.dfa_dir, "dfa")
        
        # NFA'ları yükle
        self._load_automata_from_dir(self.nfa_dir, "nfa")
        
        return self.loaded_automata
        
    def _load_automata_from_dir(self, directory: str, automata_type: str) -> None:
        """
        Belirtilen dizindeki XML otomata dosyalarını yükler.
        
        Args:
            directory: Otomata XML dosyalarının bulunduğu dizin
            automata_type: Otomata tipi ("dfa" veya "nfa")
        """
        if not os.path.exists(directory):
            logger.warning(f"{directory} dizini bulunamadı.")
            return
            
        for filename in os.listdir(directory):
            if filename.endswith(".xml") and filename != "__init__.py":
                filepath = os.path.join(directory, filename)
                try:
                    automata_def = self._parse_automata_xml(filepath)
                    if automata_def:
                        automata_id = automata_def.get("id", os.path.splitext(filename)[0])
                        self.loaded_automata[automata_id] = automata_def
                        logger.info(f"{automata_id} otomatası başarıyla yüklendi.")
                except Exception as e:
                    logger.error(f"{filename} dosyasını yüklerken hata: {str(e)}")
    
    def _parse_automata_xml(self, xml_path: str) -> Dict[str, Any]:
        """
        XML dosyasından otomata tanımını ayrıştırır.
        
        Args:
            xml_path: Otomata XML dosyasının yolu
            
        Returns:
            Otomata tanımını içeren sözlük
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            automata_def = {
                "id": root.get("id"),
                "name": root.get("name"),
                "type": root.get("type"),
                "states": {},
                "transitions": [],
                "initial_state": None
            }
            
            # Description bölümünü ekle
            desc_elem = root.find("description")
            if desc_elem is not None and desc_elem.text:
                automata_def["description"] = desc_elem.text.strip()
            
            # Metadata bölümünü ekle
            metadata_elem = root.find("metadata")
            if metadata_elem is not None:
                automata_def["metadata"] = {}
                for child in metadata_elem:
                    automata_def["metadata"][child.tag] = child.text
            
            # States bölümünü işle
            states_elem = root.find("states")
            if states_elem is not None:
                for state_elem in states_elem.findall("state"):
                    state_id = state_elem.get("id")
                    state_def = {
                        "id": state_id,
                        "name": state_elem.get("name", state_id),
                        "initial": state_elem.get("initial") == "true"
                    }
                    
                    # Initial state ise kaydet
                    if state_def["initial"]:
                        automata_def["initial_state"] = state_id
                    
                    # Description bölümünü ekle
                    state_desc = state_elem.find("description")
                    if state_desc is not None and state_desc.text:
                        state_def["description"] = state_desc.text.strip()
                    
                    # Event handlers
                    for handler in ["onEntry", "onExit"]:
                        handler_elem = state_elem.find(handler)
                        if handler_elem is not None and handler_elem.text:
                            state_def[handler] = handler_elem.text
                    
                    # State metadata
                    state_meta = state_elem.find("metadata")
                    if state_meta is not None:
                        state_def["metadata"] = {}
                        for meta_child in state_meta:
                            state_def["metadata"][meta_child.tag] = meta_child.text
                    
                    automata_def["states"][state_id] = state_def
            
            # Transitions bölümünü işle
            transitions_elem = root.find("transitions")
            if transitions_elem is not None:
                for trans_elem in transitions_elem.findall("transition"):
                    trans_def = {
                        "from": trans_elem.get("from"),
                        "to": trans_elem.get("to"),
                        "event": trans_elem.get("event")
                    }
                    
                    # Condition bölümünü ekle
                    condition_elem = trans_elem.find("condition")
                    if condition_elem is not None and condition_elem.text:
                        trans_def["condition"] = condition_elem.text.strip()
                    
                    # Action bölümünü ekle
                    action_elem = trans_elem.find("action")
                    if action_elem is not None and action_elem.text:
                        trans_def["action"] = action_elem.text.strip()
                    
                    automata_def["transitions"].append(trans_def)
            
            return automata_def
            
        except Exception as e:
            logger.error(f"XML ayrıştırma hatası: {str(e)}")
            raise
            
    def get_automata(self, automata_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirtilen ID'ye sahip otomatayı döndürür.
        
        Args:
            automata_id: Otomata ID'si
            
        Returns:
            Otomata tanımı veya None (bulunamazsa)
        """
        return self.loaded_automata.get(automata_id)
        
    def get_automata_list(self) -> List[Tuple[str, str]]:
        """
        Yüklü tüm otomataların ID ve isimlerini listeler.
        
        Returns:
            (id, name) çiftlerinden oluşan liste
        """
        result = []
        for aid, automata in self.loaded_automata.items():
            result.append((aid, automata.get("name", aid)))
        return result

    def load_automata(self, xml_path: str) -> Optional[Dict[str, Any]]:
        """
        Belirtilen XML dosyasından tek bir otomatayı yükler.
        
        Args:
            xml_path: Otomata XML dosyasının yolu
            
        Returns:
            Yüklenen otomata tanımı veya None (hata durumunda)
        """
        try:
            automata_def = self._parse_automata_xml(xml_path)
            if automata_def:
                automata_id = automata_def.get("id")
                self.loaded_automata[automata_id] = automata_def
                logger.info(f"{automata_id} otomatası başarıyla yüklendi.")
                return automata_def
        except Exception as e:
            logger.error(f"{xml_path} dosyasını yüklerken hata: {str(e)}")
        return None
        
    def load_automatas(self, xml_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Belirtilen XML dosyalarından otomataları yükler.
        
        Args:
            xml_paths: Otomata XML dosyalarının yollarının listesi
            
        Returns:
            Yüklenen otomataların bir sözlüğü (otomata_id -> otomata_tanımı)
        """
        result = {}
        for xml_path in xml_paths:
            try:
                automata_def = self._parse_automata_xml(xml_path)
                if automata_def:
                    automata_id = automata_def.get("id")
                    if automata_id:
                        self.loaded_automata[automata_id] = automata_def
                        result[automata_id] = automata_def
                        logger.info(f"{automata_id} otomatası başarıyla yüklendi.")
                    else:
                        logger.warning(f"{xml_path} otomatası için geçerli bir ID bulunamadı.")
            except Exception as e:
                logger.error(f"{xml_path} dosyasını yüklerken hata: {str(e)}")
        
        return result 