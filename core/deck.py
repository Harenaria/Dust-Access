import random
import pandas as pd
from core import card
from core import enums


# noinspection PyTypeChecker
class Deck:
    def __init__(self, deckID:int):
        self.cards = list()
        df = pd.read_csv("".join(['./data/', str(deckID), '.csv']))
        equip_df = df.query('Type == "Head" or Type == "Chest" or Type == "Bracers" or Type == "Boots" or Type == "Off-Hand"', inplace=False)
        weapon_df = df.query('Type == "Weapon" or Type == "Dual"', inplace=False)
        skill_df = df.query('Type == "Skill" or Type == "Instant"', inplace=False)
        cantrip_df = df.query('Type == "Cantrip"', inplace=False)
        for i in range(len(equip_df)):
            for n in range(equip_df['in_deck'].iloc[i]):
                self.cards.append(card.EquipCard(
                    equip_df['Name'].iloc[i],
                    equip_df['Text'].iloc[i],
                    equip_df['Flavor'].iloc[i],
                    enums.AccessorClass(equip_df['Class'].iloc[i]),
                    enums.CardType(equip_df['Type'].iloc[i]),
                    equip_df['Level'].iloc[i],
                    equip_df['CD'].iloc[i],
                    equip_df['CD'].iloc[i],
                    equip_df['OnPlay'].iloc[i],
                    equip_df['OnActivate'].iloc[i],
                    equip_df['OnNextTurn'].iloc[i],
                    equip_df['OnNextPlayerTurn'].iloc[i],
                    equip_df['OnRemove'].iloc[i],
                    equip_df['WhileinPlay'].iloc[i],
                    equip_df['DurabilityIncrease'].iloc[i],
                    equip_df['PowerIncrease'].iloc[i],
                    equip_df['EfficiencyIncrease'].iloc[i],
                    equip_df['TenacityIncrease'].iloc[i],
                    equip_df['SensitivityIncrease'].iloc[i],
                ))
        for i in range(len(weapon_df)):
            for n in range(weapon_df['in_deck'].iloc[i]):
                self.cards.append(card.WeaponCard(
                    weapon_df['Name'].iloc[i],
                    weapon_df['Text'].iloc[i],
                    weapon_df['Flavor'].iloc[i],
                    enums.AccessorClass(weapon_df['Class'].iloc[i]),
                    enums.CardType(weapon_df['Type'].iloc[i]),
                    weapon_df['Level'].iloc[i],
                    weapon_df['CD'].iloc[i],
                    weapon_df['CD'].iloc[i],
                    weapon_df['OnPlay'].iloc[i],
                    weapon_df['OnActivate'].iloc[i],
                    weapon_df['OnNextTurn'].iloc[i],
                    weapon_df['OnNextPlayerTurn'].iloc[i],
                    weapon_df['OnRemove'].iloc[i],
                    weapon_df['WhileinPlay'].iloc[i],
                    weapon_df['DurabilityIncrease'].iloc[i],
                    weapon_df['PowerIncrease'].iloc[i],
                    weapon_df['EfficiencyIncrease'].iloc[i],
                    weapon_df['TenacityIncrease'].iloc[i],
                    weapon_df['SensitivityIncrease'].iloc[i],
                    weapon_df['is2Handed'].iloc[i],
                    enums.Stats(weapon_df['AtkStat'].iloc[i]),
                    enums.Scaling(weapon_df['AtkFunc'].iloc[i]),
                    weapon_df['AtkCoeff'].iloc[i],
                    weapon_df['OnHit'].iloc[i],
                    weapon_df['OnMiss'].iloc[i]
                ))
        
        for i in range(len(skill_df)):
            isInstant = 1 if (skill_df['Type'].iloc[i] == "Instant") else 0
            for n in range(skill_df['in_deck'].iloc[i]):
                self.cards.append(card.SkillCard(
                    skill_df['Name'].iloc[i],
                    skill_df['Text'].iloc[i],
                    skill_df['Flavor'].iloc[i],
                    enums.AccessorClass(skill_df['Class'].iloc[i]),
                    enums.CardType(skill_df['Type'].iloc[i]),
                    skill_df['Level'].iloc[i],
                    skill_df['CD'].iloc[i],
                    skill_df['CD'].iloc[i],
                    skill_df['OnPlay'].iloc[i],
                    skill_df['OnActivate'].iloc[i],
                    skill_df['OnNextTurn'].iloc[i],
                    skill_df['OnNextPlayerTurn'].iloc[i],
                    skill_df['OnRemove'].iloc[i],
                    skill_df['WhileinPlay'].iloc[i],
                    isInstant,
                    skill_df['ChainsWith'].iloc[i],
                    skill_df['OnHit'].iloc[i],
                    skill_df['OnMiss'].iloc[i]
                ))
        for i in range(len(cantrip_df)):
            for n in range(cantrip_df['in_deck'].iloc[i]):
                self.cards.append(card.CantripCard(
                    cantrip_df['Name'].iloc[i],
                    cantrip_df['Text'].iloc[i],
                    cantrip_df['Flavor'].iloc[i],
                    enums.AccessorClass(cantrip_df['Class'].iloc[i]),
                    enums.CardType(cantrip_df['Type'].iloc[i]),
                    cantrip_df['Level'].iloc[i],
                    cantrip_df['CD'].iloc[i],
                    cantrip_df['CD'].iloc[i],
                    cantrip_df['OnPlay'].iloc[i],
                    cantrip_df['OnActivate'].iloc[i],
                    cantrip_df['OnNextTurn'].iloc[i],
                    cantrip_df['OnNextPlayerTurn'].iloc[i],
                    cantrip_df['OnRemove'].iloc[i],
                    cantrip_df['WhileinPlay'].iloc[i],
                    cantrip_df['OnHit'].iloc[i],
                    cantrip_df['OnMiss'].iloc[i]
                ))
        
        random.shuffle(self.cards)
        print(len(self.cards))
