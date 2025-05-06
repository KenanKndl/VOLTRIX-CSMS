"""
Otomata tipleri modülü.

Bu modül, sistemdeki otomata yapılarının veri modelleri için tanımlamaları içerir.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Union, Any
from enum import Enum


class AutomataType(Enum):
    """Otomata tiplerini belirten enum sınıfı"""
    DFA = "dfa"  # Deterministik Sonlu Otomata
    NFA = "nfa"  # Non-deterministik Sonlu Otomata


@dataclass
class Transition:
    """Otomata geçişi"""
    from_state: str
    to_state: str
    event: str
    condition: Optional[str] = None
    action: Optional[str] = None


@dataclass
class State:
    """Otomata durumu"""
    id: str
    name: str
    description: Optional[str] = None
    is_initial: bool = False
    is_final: bool = False
    on_entry_action: Optional[str] = None
    on_exit_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Automata:
    """Otomata temel veri modeli"""
    id: str
    name: str
    description: Optional[str] = None
    type: AutomataType = AutomataType.DFA
    states: List[State] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    alphabet: Set[str] = field(default_factory=set)
    current_state: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initial state'i current_state olarak belirle"""
        if not self.current_state:
            for state in self.states:
                if state.is_initial:
                    self.current_state = state.id
                    break


@dataclass
class DFA(Automata):
    """Deterministik Sonlu Otomata (DFA)"""
    type: AutomataType = AutomataType.DFA


@dataclass
class NFA(Automata):
    """Non-deterministik Sonlu Otomata (NFA)"""
    type: AutomataType = AutomataType.NFA
    current_states: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initial state'i current_states setine ekle"""
        super().__post_init__()
        if self.current_state:
            self.current_states = {self.current_state}


@dataclass
class EventResult:
    """Otomata olayının sonucu"""
    success: bool
    old_state: Union[str, Set[str]]
    new_state: Union[str, Set[str]]
    message: Optional[str] = None
    executed_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict) 