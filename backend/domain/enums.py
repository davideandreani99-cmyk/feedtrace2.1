"""Enumerazioni del dominio (glossario SPEC §3 / §5)."""

from enum import StrEnum


class MaterialType(StrEnum):
    CEREALE = "CEREALE"
    SOTTOPRODOTTO = "SOTTOPRODOTTO"
    PROTEICO = "PROTEICO"
    PREMISCELA = "PREMISCELA"
    INTEGRATORE = "INTEGRATORE"
    ADDITIVO = "ADDITIVO"
    LIQUIDO = "LIQUIDO"
    ACQUA = "ACQUA"
    MANGIME_FINITO = "MANGIME_FINITO"
    PREMISCELA_MEDICATA = "PREMISCELA_MEDICATA"
    MANGIME_MEDICATO = "MANGIME_MEDICATO"


class Unit(StrEnum):
    KG = "kg"
    L = "l"


class ConsumptionPolicy(StrEnum):
    FIFO = "FIFO"
    PROPORZIONALE = "PROPORZIONALE"
    TUTTI_PRESENTI = "TUTTI_PRESENTI"


class ContainerType(StrEnum):
    SILO = "SILO"
    TRAMOGGIA = "TRAMOGGIA"
    CISTERNA = "CISTERNA"
    VASCA_BRODA = "VASCA_BRODA"
    BIG_BAG = "BIG_BAG"
    MAGAZZINO = "MAGAZZINO"


class PlantType(StrEnum):
    MISCELATORE_BATCH = "MISCELATORE_BATCH"
    BRODA = "BRODA"
    CARRO = "CARRO"


class LotRule(StrEnum):
    PER_CICLO = "PER_CICLO"
    GIORNALIERO_PER_RICETTA = "GIORNALIERO_PER_RICETTA"


class Phase(StrEnum):
    SVEZZAMENTO = "SVEZZAMENTO"
    MAGRONAGGIO = "MAGRONAGGIO"
    INGRASSO = "INGRASSO"
    SCROFE = "SCROFE"
    ALTRO = "ALTRO"


class DestinationLotStatus(StrEnum):
    APERTO = "APERTO"
    CHIUSO = "CHIUSO"
