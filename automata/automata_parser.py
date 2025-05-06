"""
Otomata XML Parser modülü.

Bu modül, sistemdeki otomata yapılarının XML tanımlarını parse etmek
için gerekli fonksiyonları içerir.
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Optional, Union, Any, Tuple
import logging

from server.automata.automata_types import (
    Automata, DFA, NFA, State, Transition, AutomataType
)

# Logger oluştur
logger = logging.getLogger("automata-parser")


def load_automata_from_xml(file_path: str) -> Union[DFA, NFA]:
    """XML dosyasından otomata yapısını yükler.
    
    Args:
        file_path: XML dosyasının yolu
        
    Returns:
        DFA veya NFA tipinde otomata nesnesi
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Otomata dosyası bulunamadı: {file_path}")
        
        # XML dosyasını oku
        automata_xml = parse_automata_xml(file_path)
        
        automata_type = automata_xml.get("type", "dfa").lower()
        
        # Otomata tipine göre uygun nesneyi oluştur
        if automata_type == "nfa":
            return NFA(
                id=automata_xml.get("id"),
                name=automata_xml.get("name"),
                description=automata_xml.get("description"),
                type=AutomataType.NFA,
                states=automata_xml.get("states", []),
                transitions=automata_xml.get("transitions", []),
                alphabet=automata_xml.get("alphabet", set()),
                metadata=automata_xml.get("metadata", {})
            )
        else:
            return DFA(
                id=automata_xml.get("id"),
                name=automata_xml.get("name"),
                description=automata_xml.get("description"),
                type=AutomataType.DFA,
                states=automata_xml.get("states", []),
                transitions=automata_xml.get("transitions", []),
                alphabet=automata_xml.get("alphabet", set()),
                metadata=automata_xml.get("metadata", {})
            )
            
    except Exception as e:
        logger.error(f"Otomata yüklenirken hata oluştu: {str(e)}")
        raise


def parse_automata_xml(file_path: str) -> Dict[str, Any]:
    """XML dosyasını parse ederek otomata verilerini çıkarır.
    
    Args:
        file_path: XML dosyasının yolu
        
    Returns:
        Otomata verilerini içeren sözlük
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        automata_data = {
            "id": root.get("id"),
            "name": root.get("name"),
            "description": root.findtext("description"),
            "type": root.get("type", "dfa").lower(),
            "states": [],
            "transitions": [],
            "alphabet": set(),
            "metadata": {}
        }
        
        # Metadataları ekle
        metadata_elem = root.find("metadata")
        if metadata_elem is not None:
            for metadata in metadata_elem:
                automata_data["metadata"][metadata.tag] = metadata.text
        
        # Durumları parse et
        states_elem = root.find("states")
        if states_elem is not None:
            for state_elem in states_elem.findall("state"):
                state = State(
                    id=state_elem.get("id"),
                    name=state_elem.get("name"),
                    description=state_elem.findtext("description"),
                    is_initial=state_elem.get("initial", "false").lower() == "true",
                    is_final=state_elem.get("final", "false").lower() == "true",
                    on_entry_action=state_elem.findtext("onEntry"),
                    on_exit_action=state_elem.findtext("onExit"),
                    metadata={}
                )
                
                # Durum metadatalarını ekle
                state_metadata_elem = state_elem.find("metadata")
                if state_metadata_elem is not None:
                    for metadata in state_metadata_elem:
                        state.metadata[metadata.tag] = metadata.text
                
                automata_data["states"].append(state)
        
        # Geçişleri parse et
        transitions_elem = root.find("transitions")
        if transitions_elem is not None:
            for transition_elem in transitions_elem.findall("transition"):
                transition = Transition(
                    from_state=transition_elem.get("from"),
                    to_state=transition_elem.get("to"),
                    event=transition_elem.get("event"),
                    condition=transition_elem.findtext("condition"),
                    action=transition_elem.findtext("action")
                )
                
                automata_data["transitions"].append(transition)
                
                # Alfabeye olayı ekle
                automata_data["alphabet"].add(transition.event)
        
        return automata_data
    
    except ET.ParseError as e:
        logger.error(f"XML parse hatası: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Otomata parse edilirken hata oluştu: {str(e)}")
        raise 