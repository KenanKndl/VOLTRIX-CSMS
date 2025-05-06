"""
Otomata işleme motoru.

Bu modül, XML'den yüklenen otomata tanımlarını çalıştıran ve
durum geçişlerini yöneten sınıfları içerir.
"""

import logging
from typing import Dict, Any, List, Callable, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class AutomataEngine:
    """
    Otomata tanımlarını yürüten ve durum geçişlerini yöneten sınıf.
    """
    
    def __init__(self, automata_def: Dict[str, Any]):
        """
        AutomataEngine sınıfını başlatır.
        
        Args:
            automata_def: Otomata tanımını içeren sözlük
        """
        self.automata_def = automata_def
        self.id = automata_def.get("id", "unnamed_automata")
        self.name = automata_def.get("name", self.id)
        self.type = automata_def.get("type", "dfa")  # 'dfa' veya 'nfa'
        
        # Mevcut durum ve geçmiş
        self.current_states = set()  # NFA'lar için çoklu durum desteği
        initial_state = automata_def.get("initial_state")
        
        if initial_state:
            self.current_states.add(initial_state)
        else:
            # Initial state yoksa, 'initial="true"' olan bir state bul
            for state_id, state_def in automata_def.get("states", {}).items():
                if state_def.get("initial", False):
                    self.current_states.add(state_id)
                    break
        
        # Durum geçiş geçmişi
        self.state_history = []
        
        # Eylem işleyicileri (callbacks)
        self.action_handlers = {}
        self.condition_handlers = {}
        self.event_handlers = {}
        
        logger.info(f"{self.name} otomatası başlatıldı. Başlangıç durumu: {self.current_states}")
        
    def register_action_handler(self, action_name: str, handler: Callable) -> None:
        """
        Eylem işleyici fonksiyonu kaydeder.
        
        Args:
            action_name: Eylem adı
            handler: Eylemi gerçekleştirecek fonksiyon
        """
        self.action_handlers[action_name] = handler
        
    def register_condition_handler(self, condition_name: str, handler: Callable) -> None:
        """
        Koşul değerlendirme fonksiyonu kaydeder.
        
        Args:
            condition_name: Koşul adı
            handler: Koşulu değerlendirecek fonksiyon
        """
        self.condition_handlers[condition_name] = handler
        
    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """
        Olay işleyici fonksiyonu kaydeder.
        
        Args:
            event_name: Olay adı
            handler: Olayı işleyecek fonksiyon
        """
        self.event_handlers[event_name] = handler
    
    def trigger_event(self, event: str, context: Dict[str, Any] = None) -> bool:
        """
        Otomata için bir olay tetikler ve durum geçişi yapar.
        
        Args:
            event: Tetiklenecek olay
            context: Olay bağlamı
            
        Returns:
            bool: Olay tetiklendiyse True, aksi halde False
        """
        if not context:
            context = {}
        
        # Mevcut durumu al
        if not self.current_states:
            logger.warning(f"{self.name}: Mevcut durum bulunamadı")
            return False
        
        current_state_id = next(iter(self.current_states))
        
        # Mevcut durum için geçerli geçişleri bul
        valid_transitions = []
        
        for transition in self.automata_def.get("transitions", []):
            if transition.get("from") == current_state_id and transition.get("event") == event:
                valid_transitions.append(transition)
        
        if not valid_transitions:
            logger.warning(f"{self.name}: '{current_state_id}' durumundan '{event}' olayı için geçiş yok")
            return False
        
        # İlk geçişi kullan
        transition = valid_transitions[0]
        target_state_id = transition.get("to")
        
        # Durum geçişi
        prev_state = current_state_id
        self.current_states.clear()
        self.current_states.add(target_state_id)
        
        # Geçiş geçmişini güncelle
        transition_info = {
            "from": prev_state,
            "to": target_state_id,
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        self.state_history.append(transition_info)
        
        logger.info(f"{self.name}: '{prev_state}' -> '{target_state_id}' ({event})")
        return True
    
    def _apply_transition(self, transition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Durum geçişini uygular.
        
        Args:
            transition: Uygulanacak geçiş tanımı
            context: Geçiş bağlamını içeren veri
            
        Returns:
            İşlem başarılıysa True, değilse False
        """
        try:
            from_state = transition.get("from")
            to_state = transition.get("to")
            event = transition.get("event")
            
            # Çıkış olayını işle (from_state için onExit)
            from_state_def = self.automata_def.get("states", {}).get(from_state, {})
            on_exit = from_state_def.get("onExit")
            if on_exit and on_exit in self.action_handlers:
                self.action_handlers[on_exit](context)
            
            # Geçiş eylemini işle
            action = transition.get("action")
            if action and action in self.action_handlers:
                self.action_handlers[action](context)
            
            # Durumu güncelle (from_state'i kaldır, to_state'i ekle)
            if self.type == "dfa":
                self.current_states.clear()  # DFA: tek durum
            else:
                self.current_states.discard(from_state)  # NFA: birden çok durum
                
            self.current_states.add(to_state)
            
            # Giriş olayını işle (to_state için onEntry)
            to_state_def = self.automata_def.get("states", {}).get(to_state, {})
            on_entry = to_state_def.get("onEntry")
            if on_entry and on_entry in self.action_handlers:
                self.action_handlers[on_entry](context)
            
            # Geçiş geçmişine ekle
            transition_record = {
                "timestamp": datetime.now().isoformat(),
                "from": from_state,
                "to": to_state,
                "event": event
            }
            self.state_history.append(transition_record)
            
            logger.info(f"Durum geçişi: {from_state} -> {to_state} (olay: {event})")
            return True
            
        except Exception as e:
            logger.error(f"Durum geçişi sırasında hata: {str(e)}")
            return False
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Koşulu değerlendirir.
        
        Args:
            condition: Değerlendirilecek koşul adı
            context: Bağlam verisi
            
        Returns:
            Koşul doğruysa True, değilse False
        """
        try:
            if condition in self.condition_handlers:
                return self.condition_handlers[condition](context)
            return False
        except Exception as e:
            logger.error(f"Koşul değerlendirmesi sırasında hata: {str(e)}")
            return False
    
    def get_current_state(self) -> Union[str, List[str]]:
        """
        Mevcut durum(lar)ı döndürür.
        
        Returns:
            DFA için tek durum string'i, NFA için durum listesi
        """
        if self.type == "dfa":
            return next(iter(self.current_states)) if self.current_states else None
        else:
            return list(self.current_states)
    
    def get_current_state_name(self) -> str:
        """
        Mevcut durumun adını döndürür.
        
        Returns:
            str: Mevcut durumun adı
        """
        current_state_id = next(iter(self.current_states)) if self.current_states else None
        
        if not current_state_id:
            return "UNKNOWN"
        
        # State bilgisini al
        state_def = self.automata_def.get("states", {}).get(current_state_id, {})
        
        # Durum adını döndür
        return state_def.get("name", current_state_id)
    
    def get_possible_events(self) -> List[str]:
        """
        Mevcut durumda tetiklenebilecek olayları listeler.
        
        Returns:
            list: Tetiklenebilecek olayların listesi
        """
        if not self.current_states:
            return []
        
        current_state_id = next(iter(self.current_states))
        
        # Mevcut durumdan yapılabilecek tüm geçişlerin olaylarını topla
        events = []
        for transition in self.automata_def.get("transitions", []):
            if transition.get("from") == current_state_id:
                event = transition.get("event")
                if event and event not in events:
                    events.append(event)
        
        return events
    
    def get_state_history(self) -> List[Dict[str, Any]]:
        """
        Durum geçiş geçmişini döndürür.
        
        Returns:
            Durum geçişlerinin kronolojik listesi
        """
        return self.state_history
    
    def reset(self) -> None:
        """
        Otomatayı başlangıç durumuna sıfırlar.
        """
        self.current_states.clear()
        initial_state = self.automata_def.get("initial_state")
        
        if initial_state:
            self.current_states.add(initial_state)
        else:
            # Initial state yoksa, 'initial="true"' olan bir state bul
            for state_id, state_def in self.automata_def.get("states", {}).items():
                if state_def.get("initial", False):
                    self.current_states.add(state_id)
                    break
        
        self.state_history = []
        logger.info(f"{self.name} otomatası sıfırlandı. Yeni durum: {self.current_states}")
        
    def get_state_metadata(self, state_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir durumun metadata bilgilerini döndürür.
        
        Args:
            state_id: Durum ID'si
            
        Returns:
            Durum metadata'sı veya None
        """
        state_def = self.automata_def.get("states", {}).get(state_id)
        if state_def:
            return state_def.get("metadata", {})
        return None 