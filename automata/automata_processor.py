"""
Otomata İşlemci modülü.

Bu modül, sistemdeki otomata yapılarının çalışmasını ve olay işleme
fonksiyonlarını içerir.
"""

import logging
from typing import Dict, List, Set, Optional, Union, Any, Callable

from server.automata.automata_types import (
    Automata, DFA, NFA, State, Transition, AutomataType, EventResult
)

# Logger oluştur
logger = logging.getLogger("automata-processor")

# Koşul fonksiyonları için global registry
condition_functions: Dict[str, Callable] = {}

# Eylem fonksiyonları için global registry
action_functions: Dict[str, Callable] = {}


def register_condition(name: str, func: Callable) -> None:
    """Koşul fonksiyonu kaydeder.
    
    Args:
        name: Koşul fonksiyonunun adı
        func: Koşul fonksiyonu
    """
    condition_functions[name] = func
    logger.debug(f"Koşul fonksiyonu kaydedildi: {name}")


def register_action(name: str, func: Callable) -> None:
    """Eylem fonksiyonu kaydeder.
    
    Args:
        name: Eylem fonksiyonunun adı
        func: Eylem fonksiyonu
    """
    action_functions[name] = func
    logger.debug(f"Eylem fonksiyonu kaydedildi: {name}")


def evaluate_condition(condition_name: str, context: Dict[str, Any]) -> bool:
    """Belirlenen koşulu değerlendirir.
    
    Args:
        condition_name: Koşul fonksiyonu adı
        context: Değerlendirme bağlamı
    
    Returns:
        Koşulun sonucu (True/False)
    """
    if not condition_name:
        return True
    
    # Koşul adı null, none, veya boş string ise koşulsuz geçiş demektir
    if condition_name.lower() in ("null", "none", ""):
        return True
    
    condition_func = condition_functions.get(condition_name)
    if not condition_func:
        logger.warning(f"Koşul fonksiyonu bulunamadı: {condition_name}")
        return False
    
    try:
        result = condition_func(context)
        return bool(result)
    except Exception as e:
        logger.error(f"Koşul değerlendirilirken hata oluştu: {str(e)}")
        return False


def execute_action(action_name: str, context: Dict[str, Any]) -> None:
    """Belirlenen eylemi gerçekleştirir.
    
    Args:
        action_name: Eylem fonksiyonu adı
        context: Eylem bağlamı
    """
    if not action_name:
        return
    
    # Eylem adı null, none, veya boş string ise eylem yok demektir
    if action_name.lower() in ("null", "none", ""):
        return
    
    action_func = action_functions.get(action_name)
    if not action_func:
        logger.warning(f"Eylem fonksiyonu bulunamadı: {action_name}")
        return
    
    try:
        action_func(context)
    except Exception as e:
        logger.error(f"Eylem gerçekleştirilirken hata oluştu: {str(e)}")


def process_event(automata: Union[DFA, NFA], event: str, context: Dict[str, Any] = None) -> EventResult:
    """Otomata üzerinde olay işler.
    
    Args:
        automata: İşlenecek otomata
        event: İşlenecek olay
        context: Olay işleme bağlamı
    
    Returns:
        EventResult nesnesi
    """
    if context is None:
        context = {}
    
    # Olayı alfabede kontrol et
    if event not in automata.alphabet:
        return EventResult(
            success=False,
            old_state=get_current_state(automata),
            new_state=get_current_state(automata),
            message=f"Geçersiz olay: {event}"
        )
    
    # Otomata tipi kontrolü
    if automata.type == AutomataType.DFA:
        return _process_dfa_event(automata, event, context)
    else:
        return _process_nfa_event(automata, event, context)


def _process_dfa_event(automata: DFA, event: str, context: Dict[str, Any]) -> EventResult:
    """DFA üzerinde olay işler.
    
    Args:
        automata: İşlenecek DFA
        event: İşlenecek olay
        context: Olay işleme bağlamı
    
    Returns:
        EventResult nesnesi
    """
    old_state = automata.current_state
    executed_actions = []
    
    # Mevcut durumdan başlayan geçişleri bul
    valid_transitions = [
        t for t in automata.transitions 
        if t.from_state == old_state and t.event == event
    ]
    
    if not valid_transitions:
        return EventResult(
            success=False,
            old_state=old_state,
            new_state=old_state,
            message=f"Mevcut durumdan ({old_state}) {event} olayı için geçiş bulunamadı"
        )
    
    # Koşulları kontrol et ve geçiş yap
    for transition in valid_transitions:
        # Context'e otomata ve geçiş bilgisini ekle
        ctx = {**context, "automata": automata, "transition": transition}
        
        if evaluate_condition(transition.condition, ctx):
            # Geçiş için durumdan çıkış eylemini çalıştır
            old_state_obj = next((s for s in automata.states if s.id == old_state), None)
            if old_state_obj and old_state_obj.on_exit_action:
                execute_action(old_state_obj.on_exit_action, ctx)
                executed_actions.append(old_state_obj.on_exit_action)
            
            # Geçiş eylemini çalıştır
            if transition.action:
                execute_action(transition.action, ctx)
                executed_actions.append(transition.action)
            
            # Current state'i güncelle
            automata.current_state = transition.to_state
            
            # Yeni duruma giriş eylemini çalıştır
            new_state_obj = next((s for s in automata.states if s.id == transition.to_state), None)
            if new_state_obj and new_state_obj.on_entry_action:
                execute_action(new_state_obj.on_entry_action, ctx)
                executed_actions.append(new_state_obj.on_entry_action)
            
            return EventResult(
                success=True,
                old_state=old_state,
                new_state=automata.current_state,
                message=f"Durum geçişi başarılı: {old_state} -> {automata.current_state}",
                executed_actions=executed_actions
            )
    
    # Hiçbir geçiş koşulu sağlanmadı
    return EventResult(
        success=False,
        old_state=old_state,
        new_state=old_state,
        message=f"Koşulları sağlayan geçiş bulunamadı: {event}"
    )


def _process_nfa_event(automata: NFA, event: str, context: Dict[str, Any]) -> EventResult:
    """NFA üzerinde olay işler.
    
    Args:
        automata: İşlenecek NFA
        event: İşlenecek olay
        context: Olay işleme bağlamı
    
    Returns:
        EventResult nesnesi
    """
    old_states = automata.current_states.copy()
    executed_actions = []
    
    # Mevcut durumlardan başlayan, olay ile eşleşen tüm geçişleri bul
    valid_transitions = [
        t for t in automata.transitions 
        if t.from_state in old_states and t.event == event
    ]
    
    if not valid_transitions:
        return EventResult(
            success=False,
            old_state=old_states,
            new_state=old_states,
            message=f"Mevcut durumlardan {event} olayı için geçiş bulunamadı"
        )
    
    # Yeni durumlar seti
    new_states = set()
    
    # Koşulları kontrol et ve geçişleri yap
    for transition in valid_transitions:
        # Context'e otomata ve geçiş bilgisini ekle
        ctx = {**context, "automata": automata, "transition": transition}
        
        if evaluate_condition(transition.condition, ctx):
            # Geçiş için durumdan çıkış eylemini çalıştır
            old_state_obj = next((s for s in automata.states if s.id == transition.from_state), None)
            if old_state_obj and old_state_obj.on_exit_action:
                execute_action(old_state_obj.on_exit_action, ctx)
                executed_actions.append(old_state_obj.on_exit_action)
            
            # Geçiş eylemini çalıştır
            if transition.action:
                execute_action(transition.action, ctx)
                executed_actions.append(transition.action)
            
            # Yeni durumu ekle
            new_states.add(transition.to_state)
            
            # Yeni duruma giriş eylemini çalıştır
            new_state_obj = next((s for s in automata.states if s.id == transition.to_state), None)
            if new_state_obj and new_state_obj.on_entry_action:
                execute_action(new_state_obj.on_entry_action, ctx)
                executed_actions.append(new_state_obj.on_entry_action)
    
    if new_states:
        # Current states'i güncelle
        automata.current_states = new_states
        automata.current_state = list(new_states)[0] if new_states else None
        
        return EventResult(
            success=True,
            old_state=old_states,
            new_state=new_states,
            message=f"Durum geçişi başarılı: {old_states} -> {new_states}",
            executed_actions=executed_actions
        )
    
    # Hiçbir geçiş koşulu sağlanmadı
    return EventResult(
        success=False,
        old_state=old_states,
        new_state=old_states,
        message=f"Koşulları sağlayan geçiş bulunamadı: {event}"
    )


def get_current_state(automata: Union[DFA, NFA]) -> Union[str, Set[str]]:
    """Otomatanın mevcut durumunu döndürür.
    
    Args:
        automata: Durumu sorgulanacak otomata
    
    Returns:
        DFA için string, NFA için string seti
    """
    if automata.type == AutomataType.DFA:
        return automata.current_state
    else:
        return automata.current_states


def reset_automata(automata: Union[DFA, NFA]) -> None:
    """Otomatayı başlangıç durumuna sıfırlar.
    
    Args:
        automata: Sıfırlanacak otomata
    """
    # Başlangıç durumunu bul
    initial_state = next((s.id for s in automata.states if s.is_initial), None)
    
    if initial_state:
        automata.current_state = initial_state
        
        if automata.type == AutomataType.NFA:
            automata.current_states = {initial_state}
    else:
        logger.warning(f"Otomata için başlangıç durumu bulunamadı: {automata.id}") 