"""Molecular property tools backed by RDKit."""
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, Lipinski


COMMON_SMILES = {
    "water": "O",
    "ethanol": "CCO",
    "methanol": "CO",
    "acetone": "CC(=O)C",
    "benzene": "c1ccccc1",
    "toluene": "Cc1ccccc1",
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "caffeine": "Cn1cnc2n(C)c(=O)n(C)c(=O)c12",
    "glucose": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
    "co2": "O=C=O",
    "ethylene": "C=C",
    "propylene": "CC=C",
    "n-hexane": "CCCCCC",
    "acetic acid": "CC(=O)O",
    "ammonia": "N",
    "methane": "C",
    "ethane": "CC",
}


def _parse(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return mol


def molecular_weight(smiles: str) -> dict:
    mol = _parse(smiles)
    return {"smiles": smiles, "molecular_weight_g_per_mol": round(Descriptors.MolWt(mol), 3)}


def molecular_properties(smiles: str) -> dict:
    mol = _parse(smiles)
    return {
        "smiles": smiles,
        "molecular_weight_g_per_mol": round(Descriptors.MolWt(mol), 3),
        "logP": round(Crippen.MolLogP(mol), 3),
        "h_bond_donors": Lipinski.NumHDonors(mol),
        "h_bond_acceptors": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "tpsa": round(Descriptors.TPSA(mol), 3),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
    }


def name_to_smiles(name: str) -> dict:
    key = name.strip().lower()
    if key not in COMMON_SMILES:
        return {
            "error": f"'{name}' not in curated dictionary. Known: {sorted(COMMON_SMILES.keys())}"
        }
    return {"name": key, "smiles": COMMON_SMILES[key]}
