import streamlit as st
import random
from dataclasses import dataclass, asdict
from typing import List, Optional

import plotly.graph_objects as go

# ---------- Page config & global CSS ----------

st.set_page_config(page_title="National Collector RPG", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background-image: radial-gradient(circle at top left, #ffffff 0, #f7f7ff 50%, #f0f0ff 100%);
    }
    .stTable tbody tr:nth-child(even) {
        background-color: #fafaff;
    }
    .stTable th {
        background-color: #f0f0ff !important;
    }
    button[kind="primary"] {
        border-radius: 999px !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Data models ----------

@dataclass
class Card:
    name: str
    player: str
    year: int
    set_name: str
    true_value: float
    ask_price: float


@dataclass
class Encounter:
    npc_type: str
    mood: str
    zone: str
    cards: List[Card]
    round: int
    active: bool
    history: List[str]


# ---------- Core constants ----------

ZONES = [
    "Vintage Alley",
    "Modern Showcases",
    "Dollar Boxes",
    "Corporate Pavilion",
    "Trade Night",
]

NPC_TYPES = ["Dealer", "Kid Collector", "Flipper", "PC Supercollector"]
MOODS = ["happy", "neutral", "grumpy"]

ZONE_META = {
    "Vintage Alley": {"icon": "📜", "color": "#b08968"},
    "Modern Showcases": {"icon": "💎", "color": "#1d3557"},
    "Dollar Boxes": {"icon": "📦", "color": "#2a9d8f"},
    "Corporate Pavilion": {"icon": "🏢", "color": "#6c757d"},
    "Trade Night": {"icon": "🌙", "color": "#ffb703"},
}

NPC_META = {
    "Dealer": {"icon": "🧢"},
    "Kid Collector": {"icon": "🧒"},
    "Flipper": {"icon": "💼"},
    "PC Supercollector": {"icon": "🏆"},
}

NPC_BEHAVIOR = {
    "Dealer": {"overask": (1.2, 1.4), "min_pct": 0.9},
    "Kid Collector": {"overask": (1.0, 1.2), "min_pct": 0.8},
    "Flipper": {"overask": (1.25, 1.5), "min_pct": 0.95},
    "PC Supercollector": {"overask": (1.15, 1.3), "min_pct": 0.85},
}

GYMS = [
    {
        "id": "vintage_titan",
        "name": "Vintage Titan Table",
        "boss": "Vintage Titan",
        "zone": "Vintage Alley",
        "required_level": 2,
        "description": "A legendary vintage dealer who only respects sharp negotiation on 50s and 60s cardboard.",
    },
    {
        "id": "chrome_master",
        "name": "Chrome Master Showcase",
        "boss": "Chrome Master",
        "zone": "Modern Showcases",
        "required_level": 2,
        "description": "A slab-heavy modern guru with cases full of Prizm, Select, and Optic.",
    },
    {
        "id": "dollar_box_duke",
        "name": "Dollar Box Gauntlet",
        "boss": "Dollar Box Duke",
        "zone": "Dollar Boxes",
        "required_level": 3,
        "description": "The master of value boxes, where sleepers hide and margins are made.",
    },
    {
        "id": "trade_night_boss",
        "name": "Trade Night Main Event",
        "boss": "Trade Night Boss",
        "zone": "Trade Night",
        "required_level": 3,
        "description": "Runs the biggest trade night; binder-for-binder deals only.",
    },
]

ELITE_FOUR = [
    {
        "id": "box_breaker",
        "name": "Influencer 1: Box Breaker",
        "boss": "Box Breaker",
        "description": "A streamer who wants you to buy wax instead of singles—can you negotiate a fair rip?",
        "required_level": 4,
    },
    {
        "id": "content_flipper",
        "name": "Influencer 2: Content Flipper",
        "boss": "Content Flipper",
        "description": "Lives by comps and thumbnails; can you get a real deal past the content?",
        "required_level": 5,
    },
    {
        "id": "analytics_nerd",
        "name": "Influencer 3: Analytics Nerd",
        "boss": "Analytics Nerd",
        "description": "Charts, pop reports, and spreadsheets—your every move is being modeled.",
        "required_level": 6,
    },
    {
        "id": "show_vlogger",
        "name": "Influencer 4: Show Vlogger",
        "boss": "Show Vlogger",
        "description": "Cares about the story of the deal more than the margin; style matters.",
        "required_level": 7,
    },
]

CHAMPION = {
    "id": "national_whale",
    "name": "The National Whale",
    "boss": "The National Whale",
    "description": "The biggest buyer in the room with impossible showcases and zero tolerance for weak deals.",
    "required_level": 8,
}

# ---------- Game helpers ----------

def base_player_state():
    return {
        "name": "",
        "favorite": "",
        "cash": 1000.0,
        "stamina": 100,
        "day": 1,
        "time_block": "Morning",
        "xp": 0,
        "level": 1,
        "goals": {
            "target_pc_card": "",
            "profit_target": 400.0,
        },
        "collection": [],
        "profit": 0.0,
        "build_locked": False,
        "badges": [],
        "elite_defeated": [],
        "champion_defeated": False,
        "attributes": {
            "Negotiation": 50,
            "People Skills": 50,
            "Card Knowledge": 50,
            "Hustle": 50,
        },
        "subjects": {
            "Vintage Baseball": 0,
            "Vintage Football": 0,
            "Vintage Basketball": 0,
            "Vintage Hockey": 0,
            "Modern Baseball": 0,
            "Modern Football": 0,
            "Modern Basketball": 0,
            "Modern Hockey": 0,
            "Soccer": 0,
            "Other / TCG / Non‑sport": 0,
        },
    }


def init_state():
    st.session_state.player = base_player_state()
    st.session_state.encounter: Optional[Encounter] = None


def advance_flavor_time():
    time_order = ["Morning", "Afternoon", "Evening"]
    p = st.session_state.player
    idx = time_order.index(p["time_block"])
    if idx < len(time_order) - 1:
        p["time_block"] = time_order[idx + 1]
    else:
        p["time_block"] = "Morning"
        p["day"] += 1


def add_xp(amount: int):
    p = st.session_state.player
    p["xp"] += amount
    thresholds = [0, 50, 150, 300, 500, 750]
    new_level = p["level"]
    for i, t in enumerate(thresholds, start=1):
        if p["xp"] >= t:
            new_level = i
    if new_level > p["level"]:
        p["level"] = new_level
        advance_flavor_time()


def subject_score_for_zone(zone: str, subjects: dict) -> float:
    if zone == "Vintage Alley":
        total = (
            subjects["Vintage Baseball"] +
            subjects["Vintage Football"] +
            subjects["Vintage Basketball"] +
            subjects["Vintage Hockey"]
        )
        return total / 400.0
    if zone == "Modern Showcases":
        total = (
            subjects["Modern Baseball"] +
            subjects["Modern Football"] +
            subjects["Modern Basketball"] +
            subjects["Modern Hockey"] +
            subjects["Soccer"]
        )
        return total / 500.0
    if zone == "Dollar Boxes":
        total = (
            subjects["Modern Baseball"] +
            subjects["Modern Football"] +
            subjects["Modern Basketball"] +
            subjects["Modern Hockey"] +
            subjects["Soccer"] +
            subjects["Other / TCG / Non‑sport"]
        )
        return total / 600.0
    if zone == "Corporate Pavilion":
        return sum(subjects.values()) / 1000.0
    if zone == "Trade Night":
        total = sum(subjects.values()) + subjects["Other / TCG / Non‑sport"]
        return total / 1100.0
    return 0.0


def grant_xp_for_deal(zone: str, margin: float, is_trade: bool, is_sale: bool = False):
    player = st.session_state.player
    attrs = player["attributes"]
    subjects = player["subjects"]
    hustle = attrs["Hustle"]

    base = 5

    zone_factor = {
        "Dollar Boxes": 0.8,
        "Vintage Alley": 1.1,
        "Modern Showcases": 1.0,
        "Corporate Pavilion": 1.0,
        "Trade Night": 1.1,
    }.get(zone, 1.0)

    margin_xp = max(0.0, margin / 20.0)
    margin_xp = min(margin_xp, 40.0)

    trade_bonus = 1.3 if is_trade else 1.0
    if is_sale:
        trade_bonus = 0.9

    hustle_bonus = 1.0 + hustle / 500.0
    zone_subj = subject_score_for_zone(zone, subjects)
    lane_bonus = 1.0 + 0.5 * zone_subj

    total_xp = int((base + margin_xp) * zone_factor * trade_bonus * hustle_bonus * lane_bonus)
    if total_xp > 0:
        add_xp(total_xp)


def generate_cards_for_zone(zone: str, npc_type: str) -> List[Card]:
    base_cards = []
    if zone == "Vintage Alley":
        base_cards = [
            ("HOF RB Rookie", "Legend RB", 1958, "Topps", 500.0),
            ("Iconic OF RC", "Legend OF", 1952, "Topps", 1500.0),
        ]
    elif zone == "Modern Showcases":
        base_cards = [
            ("Star QB Rookie", "Star QB", 2020, "Prizm", 250.0),
            ("Young Star RC", "Young Star", 2022, "Select", 120.0),
        ]
    elif zone == "Dollar Boxes":
        base_cards = [
            ("Sleeper WR", "WR Prospect", 2023, "Donruss", 5.0),
            ("Bench Shooter", "Role Player", 2021, "Hoops", 2.0),
        ]
    elif zone == "Corporate Pavilion":
        base_cards = [
            ("Show Exclusive", "Promo Player", 2025, "National Promo", 40.0),
        ]
    else:
        base_cards = [
            ("PC Parallel", "Your PC Guy", 2019, "Optic", 80.0),
            ("Random RC", "Random Rookie", 2021, "Mosaic", 25.0),
        ]

    behavior = NPC_BEHAVIOR.get(npc_type, {"overask": (1.1, 1.4)})
    lo, hi = behavior["overask"]

    cards = []
    for name, player_name, year, set_name, true_value in base_cards:
        ask = round(true_value * random.uniform(lo, hi), 2)
        cards.append(Card(name, player_name, year, set_name, true_value, ask))
    return cards


def init_encounter_state(enc: Encounter, tough_multiplier: float = 1.0):
    enc.npc_hp = int(100 * tough_multiplier)
    enc.npc_max_hp = int(100 * tough_multiplier)
    enc.price_factor = 1.0 * tough_multiplier
    enc.patience = 5 + int(2 * tough_multiplier)


def start_encounter(zone: str):
    npc_type = random.choice(NPC_TYPES)
    mood = random.choice(MOODS)
    cards = generate_cards_for_zone(zone, npc_type)
    enc = Encounter(
        npc_type=npc_type,
        mood=mood,
        zone=zone,
        cards=cards,
        round=1,
        active=True,
        history=[f"You approach a {npc_type} in {zone}. They seem {mood}."],
    )
    init_encounter_state(enc)
    st.session_state.encounter = enc


def has_big_deal(stage_id: str) -> bool:
    return stage_id in st.session_state.player["badges"]


def mark_big_deal(stage_id: str):
    if stage_id not in st.session_state.player["badges"]:
        st.session_state.player["badges"].append(stage_id)
        add_xp(50)


def mark_influencer_won(influencer_id: str):
    if influencer_id not in st.session_state.player["elite_defeated"]:
        st.session_state.player["elite_defeated"].append(influencer_id)
        add_xp(75)


def mark_whale_won():
    if not st.session_state.player["champion_defeated"]:
        st.session_state.player["champion_defeated"] = True
        add_xp(100)


def start_stage_battle(stage_id: str):
    gym = next(g for g in GYMS if g["id"] == stage_id)
    npc_type = "PC Supercollector"
    mood = random.choice(MOODS)
    zone = gym["zone"]

    cards = generate_cards_for_zone(zone, npc_type)
    for c in cards:
        c.true_value *= 2
        c.ask_price = round(c.true_value * random.uniform(1.1, 1.3), 2)

    enc = Encounter(
        npc_type=npc_type,
        mood=mood,
        zone=zone,
        cards=cards,
        round=1,
        active=True,
        history=[f"You sit down at the {gym['name']} with {gym['boss']}."],
    )
    init_encounter_state(enc, tough_multiplier=1.3)
    enc.mode = f"stage:{stage_id}"
    st.session_state.encounter = enc


def start_influencer_battle(influencer_id: str):
    elite = next(e for e in ELITE_FOUR if e["id"] == influencer_id)
    npc_type = "Dealer"
    mood = "neutral"
    zone = "Modern Showcases"
    cards = generate_cards_for_zone(zone, npc_type)
    for c in cards:
        c.true_value *= 3
        c.ask_price = round(c.true_value * random.uniform(1.05, 1.25), 2)

    enc = Encounter(
        npc_type=npc_type,
        mood=mood,
        zone=zone,
        cards=cards,
        round=1,
        active=True,
        history=[f"You’re on camera with {elite['boss']} ({elite['name']})."],
    )
    init_encounter_state(enc, tough_multiplier=1.6)
    enc.mode = f"influencer:{influencer_id}"
    st.session_state.encounter = enc


def start_whale_battle():
    champ = CHAMPION
    npc_type = "PC Supercollector"
    mood = "neutral"
    zone = "Modern Showcases"
    cards = generate_cards_for_zone(zone, npc_type)
    for c in cards:
        c.true_value *= 4
        c.ask_price = round(c.true_value * random.uniform(1.05, 1.2), 2)

    enc = Encounter(
        npc_type=npc_type,
        mood=mood,
        zone=zone,
        cards=cards,
        round=1,
        active=True,
        history=[f"You approach {champ['boss']} – the biggest buyer in the room."],
    )
    init_encounter_state(enc, tough_multiplier=2.0)
    enc.mode = "whale"
    st.session_state.encounter = enc


def evaluate_offer(offer: float) -> str:
    enc = st.session_state.encounter
    player = st.session_state.player
    total_true = sum(c.true_value for c in enc.cards)

    attrs = player["attributes"]
    subjects = player["subjects"]
    neg = attrs["Negotiation"]

    behavior = NPC_BEHAVIOR.get(enc.npc_type, {"min_pct": 0.85})
    base_min_pct = behavior["min_pct"]

    zone_subj = subject_score_for_zone(enc.zone, subjects)
    if enc.npc_type == "PC Supercollector":
        base_min_pct -= 0.03 * zone_subj
    elif enc.npc_type == "Flipper":
        modern_focus = (
            subjects["Modern Baseball"] +
            subjects["Modern Football"] +
            subjects["Modern Basketball"] +
            subjects["Modern Hockey"] +
            subjects["Soccer"]
        ) / 500.0
        base_min_pct -= 0.02 * modern_focus

    mood_factor = {
        "happy": base_min_pct - 0.05,
        "neutral": base_min_pct,
        "grumpy": base_min_pct + 0.05,
    }[enc.mood]

    hp_factor = max(0.5, enc.npc_hp / enc.npc_max_hp)
    effective_min_pct = mood_factor * enc.price_factor * hp_factor

    neg_discount = (neg - 50) / 500.0
    zone_subj_discount = zone_subj * 0.08

    threshold_pct = max(0.6, effective_min_pct - neg_discount - zone_subj_discount)
    threshold = total_true * threshold_pct

    if offer >= threshold:
        return "accept"
    elif offer >= threshold * 0.8:
        return "counter"
    else:
        return "reject"


def finalize_deal(price_paid: float):
    enc = st.session_state.encounter
    player = st.session_state.player
    total_true = sum(c.true_value for c in enc.cards)

    player["cash"] -= price_paid
    player["profit"] += (total_true - price_paid)

    for c in enc.cards:
        player["collection"].append(asdict(c))

    enc.active = False
    enc.history.append(
        f"Deal done at ${price_paid:.2f}. Estimated value ${total_true:.2f}."
    )

    margin = total_true - price_paid
    grant_xp_for_deal(enc.zone, margin, is_trade=False, is_sale=False)

    mode = getattr(enc, "mode", None)
    if mode and margin >= 0:
        kind, ident = mode.split(":", 1) if ":" in mode else (mode, "")
        if kind == "stage":
            mark_big_deal(ident)
        elif kind == "influencer":
            mark_influencer_won(ident)
        elif kind == "whale":
            mark_whale_won()


def compute_collection_value(card_dicts):
    return sum(c.get("true_value", 0) for c in card_dicts)


def apply_move(move: str):
    enc = st.session_state.encounter
    npc = enc.npc_type
    attrs = st.session_state.player["attributes"]

    people = attrs["People Skills"]
    knowledge = attrs["Card Knowledge"]
    hustle = attrs["Hustle"]

    social_mul = 0.8 + people / 100.0
    knowledge_mul = 0.8 + knowledge / 100.0
    hustle_mul = 0.8 + hustle / 150.0

    hp_delta = 0
    price_delta = 0.0
    patience_delta = 0
    line = ""

    if move == "friendly_chat":
        base = -10
        if npc in ["Kid Collector", "PC Supercollector"]:
            base = -18
        hp_delta = int(base * social_mul)
        line = f"{npc}: 'Love talking cards.' (Deal resistance drops.)"
    elif move == "point_flaws":
        base_hp = -15
        base_price = -0.06
        if npc in ["Dealer", "Flipper"]:
            base_hp = -22
            base_price = -0.08
        hp_delta = int(base_hp * knowledge_mul)
        price_delta = base_price * knowledge_mul
        line = f"{npc}: 'Fair point.' (Price softens.)"
    elif move == "lowball_probe":
        base_hp = -8
        base_price = 0.05
        base_patience = -1
        if npc not in ["Dealer", "Flipper"]:
            base_hp = 15
            base_patience = -2
        hp_delta = int(base_hp * social_mul)
        price_delta = base_price
        patience_delta = int(base_patience * hustle_mul)
        line = f"{npc}: 'That's low.'"
    elif move == "show_comp":
        base_hp = -12
        base_price = -0.05
        hp_delta = int(base_hp * knowledge_mul)
        price_delta = base_price * knowledge_mul
        line = f"{npc}: 'Those comps are solid.'"

    enc.npc_hp = max(0, min(enc.npc_max_hp, enc.npc_hp + hp_delta))
    enc.price_factor = max(0.7, enc.price_factor + price_delta)
    enc.patience += patience_delta
    enc.history.append(line)

    if enc.patience <= 0 and enc.active:
        enc.active = False
        enc.history.append(f"{npc} has had enough and walks away from the table.")


# ---------- Initialize state ----------

if "player" not in st.session_state:
    init_state()

# ---------- Header/banner ----------

st.markdown(
    """
    <div style="
        padding:0.45rem 0.9rem;
        background:linear-gradient(90deg,#ffeb99,#ffd6cc);
        border-radius:0.6rem;
        border:1px solid #f0c36a;
        margin-bottom:0.8rem;">
        <span style="color:#b22222; font-weight:700;">National Collector RPG</span>
        <span style="color:#555; margin-left:0.4rem;">• The National Sports Collectors Convention</span>
    </div>
    """,
    unsafe_allow_html=True,
)

p = st.session_state.player

# ---------- Sidebar / HUD ----------

with st.sidebar:
    st.markdown("### Trip HUD")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown(f"**{p['name'] or 'Collector'}**")
        st.caption(p["favorite"] or "Set your favorite on Intro page.")
    with col_b:
        if st.button("Reset run", key="reset_run"):
            init_state()
            st.experimental_rerun()
        st.button("Help", key="help_btn")

    st.markdown("---")

    st.markdown("**Level & XP**")
    thresholds = [0, 50, 150, 300, 500, 750, 1100]
    lvl = p["level"]
    xp = p["xp"]
    prev_t = thresholds[max(0, lvl - 1)]
    next_t = thresholds[min(len(thresholds) - 1, lvl)]
    span = max(1, next_t - prev_t)
    pct_to_next = min(1.0, (xp - prev_t) / span)
    st.write(f"Level {lvl} • XP {xp}/{next_t}")
    st.progress(pct_to_next)

    st.markdown("---")

    st.markdown("**Resources**")
    cash_col, stam_col = st.columns(2)
    with cash_col:
        st.caption("Cash")
        st.write(f"${p['cash']:.0f}")
    with stam_col:
        st.caption("Stamina")
        st.progress(min(1.0, p["stamina"] / 100.0))
    st.caption(f"Trip profit: ${p['profit']:.0f}")

    st.markdown("---")

    attrs_sidebar = p["attributes"]
    gauge_fig = go.Figure()

    gauge_fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=attrs_sidebar["Negotiation"],
        title={"text": "Negotiation"},
        domain={"row": 0, "column": 0},
        gauge={"axis": {"range": [0, 100]}}
    ))
    gauge_fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=attrs_sidebar["People Skills"],
        title={"text": "People"},
        domain={"row": 0, "column": 1},
        gauge={"axis": {"range": [0, 100]}}
    ))
    gauge_fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=attrs_sidebar["Card Knowledge"],
        title={"text": "Knowledge"},
        domain={"row": 1, "column": 0},
        gauge={"axis": {"range": [0, 100]}}
    ))
    gauge_fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=attrs_sidebar["Hustle"],
        title={"text": "Hustle"},
        domain={"row": 1, "column": 1},
        gauge={"axis": {"range": [0, 100]}}
    ))

    gauge_fig.update_layout(
        grid={"rows": 2, "columns": 2, "pattern": "independent"},
        margin=dict(l=10, r=10, t=20, b=10),
        height=260,
    )

    st.markdown("**Skills**")
    st.plotly_chart(gauge_fig, use_container_width=True)

    st.markdown("---")

    st.markdown("**Goals**")
    st.caption(f"Target PC: {p['goals']['target_pc_card'] or '—'}")
    st.caption(f"Profit target: ${p['goals']['profit_target']:.0f}")
    if st.button("View collection", key="sidebar_collection"):
        st.session_state["_force_page"] = "Collection & Results"

    st.markdown("**Milestones**")
    st.caption(f"Big deals closed: {len(p['badges'])}/{len(GYMS)}")
    st.caption(f"Influencers beat: {len(p['elite_defeated'])}/{len(ELITE_FOUR)}")
    whale = "✅" if p["champion_defeated"] else "❌"
    st.caption(f"National Whale beaten: {whale}")

# ---------- Page selection ----------

if p["build_locked"]:
    page_options = ["Show Floor", "Encounter", "Big Stages & Legends", "Collection & Results"]
else:
    page_options = ["Intro & Build", "Show Floor", "Encounter", "Big Stages & Legends", "Collection & Results"]

default_index = 0
if "_force_page" in st.session_state and st.session_state["_force_page"] in page_options:
    default_index = page_options.index(st.session_state["_force_page"])
    del st.session_state["_force_page"]

page = st.radio("Go to", page_options, index=default_index, horizontal=True)

if not p["build_locked"]:
    page = "Intro & Build"

# ---------- Pages ----------

if page == "Intro & Build":
    st.title("National Collector RPG")

    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        st.image("001_image.png", use_column_width=True)
        st.markdown(
            "<p style='margin-top:0.5rem; color:#555;'>Create your collector build, then take it onto the show floor.</p>",
            unsafe_allow_html=True,
        )

    with right_col:
        st.subheader("Collector profile")

        col1, col2 = st.columns(2)
        with col1:
            p["name"] = st.text_input("Collector name", value=p["name"])
        with col2:
            p["favorite"] = st.text_input("Favorite player or team", value=p["favorite"])

        p["goals"]["target_pc_card"] = st.text_input(
            "Describe your dream PC pickup for this trip",
            value=p["goals"]["target_pc_card"],
        )

        st.markdown("---")
        st.markdown("### Core attributes (0–100)")

        attrs = p["attributes"]
        attr_budget = 250
        current_attr_total = sum(attrs.values())
        attr_remaining = attr_budget - current_attr_total
        st.caption(f"Points to allocate: {attr_remaining} (budget {attr_budget})")

        a1, a2 = st.columns(2)
        with a1:
            attrs["Negotiation"] = st.slider("Negotiation", 0, 100, attrs["Negotiation"])
            attrs["Card Knowledge"] = st.slider("Card Knowledge", 0, 100, attrs["Card Knowledge"])
        with a2:
            attrs["People Skills"] = st.slider("People Skills", 0, 100, attrs["People Skills"])
            attrs["Hustle"] = st.slider("Hustle", 0, 100, attrs["Hustle"])

        current_attr_total = sum(attrs.values())
        attr_remaining = attr_budget - current_attr_total

        st.markdown("### Subject lanes (0–100 per lane)")

        subj = p["subjects"]
        subj_budget = 300
        current_subj_total = sum(subj.values())
        subj_remaining = subj_budget - current_subj_total
        st.caption(f"Subject points left: {subj_remaining} (budget {subj_budget})")

        s1, s2 = st.columns(2)
        with s1:
            subj["Vintage Baseball"] = st.slider("Vintage Baseball", 0, 100, subj["Vintage Baseball"])
            subj["Vintage Basketball"] = st.slider("Vintage Basketball", 0, 100, subj["Vintage Basketball"])
            subj["Modern Baseball"] = st.slider("Modern Baseball", 0, 100, subj["Modern Baseball"])
            subj["Modern Basketball"] = st.slider("Modern Basketball", 0, 100, subj["Modern Basketball"])
            subj["Soccer"] = st.slider("Soccer", 0, 100, subj["Soccer"])
        with s2:
            subj["Vintage Football"] = st.slider("Vintage Football", 0, 100, subj["Vintage Football"])
            subj["Vintage Hockey"] = st.slider("Vintage Hockey", 0, 100, subj["Vintage Hockey"])
            subj["Modern Football"] = st.slider("Modern Football", 0, 100, subj["Modern Football"])
            subj["Modern Hockey"] = st.slider("Modern Hockey", 0, 100, subj["Modern Hockey"])
            subj["Other / TCG / Non‑sport"] = st.slider(
                "Other / TCG / Non‑sport", 0, 100, subj["Other / TCG / Non‑sport"]
            )

        current_subj_total = sum(subj.values())
        subj_remaining = subj_budget - current_subj_total

        if attr_remaining < 0 or subj_remaining < 0:
            st.error("You spent more than your budget. Lower at least one slider.")
        elif attr_remaining > 0 or subj_remaining > 0:
            st.info("You still have unspent points. Use the sliders to allocate them.")
        else:
            st.success("All points allocated. You can start your trip when ready.")

        st.markdown("### Trip settings")

        p["goals"]["profit_target"] = st.number_input(
            "Profit target for the trip",
            0.0, 10000.0, float(p["goals"]["profit_target"]), step=50.0,
        )
        p["cash"] = st.number_input(
            "Starting cash",
            100.0, 10000.0, float(p["cash"]), step=100.0,
        )

        start_disabled = attr_remaining != 0 or subj_remaining != 0 or not p["name"]
        if st.button("Lock in build and start trip", disabled=start_disabled):
            p["build_locked"] = True
            st.success("Build locked! Head to the Show Floor to start making deals.")

elif page == "Show Floor":
    st.title("Show Floor")

    if not p["build_locked"]:
        st.warning("Head to 'Intro & Build' first to roll your collector build.")
    else:
        left_col, right_col = st.columns([3, 2], gap="large")

        with left_col:
            st.image("002_image.png", use_column_width=True)

            st.markdown(
                "<div style='margin-top:0.6rem; padding:0.6rem 0.8rem; "
                "background-color:#ffffff; border-radius:0.7rem; "
                "border:1px solid #e0e0ff;'>"
                "<div style='font-size:0.85rem; color:#777; margin-bottom:0.25rem;'>"
                "Where do you want to go?"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            zone = st.selectbox(" ", ZONES, label_visibility="collapsed")

            if st.button("Walk to this zone"):
                start_encounter(zone)
                st.success(f"You walk over to {zone} and spot a potential deal.")
                st.info("Switch to the 'Encounter' page to negotiate.")

        with right_col:
            st.markdown("### Zones")

            for name in ZONES:
                meta = ZONE_META[name]
                st.markdown(
                    f"""
                    <div style="
                        padding:0.6rem 0.9rem;
                        margin-bottom:0.45rem;
                        border-radius:0.7rem;
                        border:1px solid #e0e0ff;
                        background-color:#ffffff;">
                        <span style="font-size:1.1rem; margin-right:0.4rem;">{meta['icon']}</span>
                        <span style="font-weight:600;">{name}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

elif page == "Encounter":
    st.title("Encounter")

    enc: Encounter = st.session_state.encounter

    if not p["build_locked"]:
        st.warning("Head to 'Intro & Build' first to roll your collector build.")
    elif enc is None or not enc.active:
        st.write("No active encounter. Head to the Show Floor or Big Stages to find a deal.")
    else:
        left_col, right_col = st.columns([3, 2], gap="large")

        with left_col:
            st.image("003_image.png", use_column_width=True)

            zone_meta = ZONE_META.get(enc.zone, {"icon": "🎪"})
            npc_meta = NPC_META.get(enc.npc_type, {"icon": "🙂"})

            st.markdown(
                f"""
                <div style="
                    margin-top:0.4rem;
                    padding:0.4rem 0.7rem;
                    background-color:#ffffff;
                    border-radius:0.6rem;
                    border:1px solid #e0e0ff;">
                    <span style="color:#777;">Day {p['day']} • {p['time_block']} • </span>
                    <span>{zone_meta['icon']} {enc.zone}</span><br/>
                    <span style="color:#b20000;">{npc_meta['icon']} A {enc.npc_type} appears.</span>
                    <span style="color:#555;"> They seem {enc.mood}.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            hp_ratio = enc.npc_hp / enc.npc_max_hp if enc.npc_max_hp > 0 else 0
            st.markdown(
                """
                <div style="margin-top:0.5rem; margin-bottom:0.15rem; color:#777; font-size:0.8rem;">
                    Deal resistance
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(hp_ratio)
            st.caption(f"Deal resistance: {enc.npc_hp}/{enc.npc_max_hp} • Patience left: {enc.patience}")

            st.markdown("#### Recent conversation")
            for line in enc.history[-5:]:
                st.write("•", line)

            st.markdown("#### Cards on the table")
            st.table(
                [
                    {
                        "Index": i,
                        "Card": c.name,
                        "Player": c.player,
                        "Year": c.year,
                        "Set": c.set_name,
                        "Ask ($)": c.ask_price,
                    }
                    for i, c in enumerate(enc.cards)
                ]
            )

        with right_col:
            st.markdown("### Your moves")

            total_ask = sum(c.ask_price for c in enc.cards)
            offer = st.number_input(
                "Cash offer",
                0.0, 10000.0, min(total_ask, p["cash"]),
                step=5.0,
                key="cash_offer_input",
            )

            b_row1 = st.columns(3, gap="small")
            friendly = b_row1[0].button("Friendly chat")
            flaws = b_row1[1].button("Point out flaws")
            lowball = b_row1[2].button("Lowball probe")

            b_row2 = st.columns(3, gap="small")
            comps = b_row2[0].button("Show comps")
            make_offer = b_row2[1].button("Make offer")
            walk = b_row2[2].button("Walk away")

            if friendly:
                apply_move("friendly_chat")
            if flaws:
                apply_move("point_flaws")
            if lowball:
                apply_move("lowball_probe")
            if comps:
                apply_move("show_comp")

            if make_offer and enc.active:
                if offer > p["cash"]:
                    st.error("You don't have that much cash.")
                else:
                    result = evaluate_offer(offer)
                    if result == "accept":
                        st.success("They accept your offer!")
                        enc.history.append(f"You offer ${offer:.2f}. They accept.")
                        finalize_deal(offer)
                    elif result == "counter":
                        counter = round(offer * random.uniform(1.05, 1.15), 2)
                        enc.history.append(
                            f"You offer ${offer:.2f}. They counter at ${counter:.2f}."
                        )
                        st.info(f"They counter at ${counter:.2f}.")
                        enc.round += 1
                    else:
                        enc.history.append(
                            f"You offer ${offer:.2f}. They reject and seem annoyed."
                        )
                        st.warning("They reject your offer.")
                        enc.round += 1
                        if enc.mood == "happy":
                            enc.mood = "neutral"
                        elif enc.mood == "neutral":
                            enc.mood = "grumpy"

            st.markdown("### Trade offer (cards + cash)")

            collection = p["collection"]
            if collection:
                trade_labels = [
                    f"{i}. {c['name']} ({c['set_name']} {c['year']}) – est ${c['true_value']:.2f}"
                    for i, c in enumerate(collection)
                ]
                selected_indices = st.multiselect(
                    "Your cards to offer",
                    options=list(range(len(collection))),
                    format_func=lambda i: trade_labels[i],
                    key="my_trade_cards",
                )
            else:
                selected_indices = []

            npc_labels = [
                f"{i}. {c.name} ({c.set_name} {c.year}) – est ${c.true_value:.2f}"
                for i, c in enumerate(enc.cards)
            ]
            target_indices = st.multiselect(
                "Cards you want from them",
                options=list(range(len(enc.cards))),
                format_func=lambda i: npc_labels[i],
                key="npc_trade_cards",
            )

            trade_cash = st.number_input(
                "Add cash to trade (optional)",
                0.0, 10000.0, 0.0,
                step=5.0,
                key="trade_cash_input",
            )

            trade_btn = st.button("Send trade offer")

            if trade_btn and enc.active:
                if not selected_indices and trade_cash <= 0:
                    st.warning("Pick at least one of your cards or add some cash to make a trade offer.")
                elif not target_indices:
                    st.warning("Pick at least one of their cards you want.")
                elif trade_cash > p["cash"]:
                    st.error("You don't have that much cash for the trade.")
                else:
                    offered_cards = [collection[i] for i in selected_indices]
                    wanted_cards = [enc.cards[i] for i in target_indices]

                    offered_value = compute_collection_value(offered_cards) + trade_cash
                    target_value = sum(c.true_value for c in wanted_cards)

                    enc.history.append(
                        f"You offer {len(offered_cards)} card(s) + ${trade_cash:.2f} "
                        f"for {len(wanted_cards)} of their card(s) "
                        f"(your offer est ${offered_value:.2f} vs their est ${target_value:.2f})."
                    )

                    if offered_value >= target_value * 0.9:
                        st.success("They like the trade and accept!")
                        for idx in sorted(selected_indices, reverse=True):
                            p["collection"].pop(idx)
                        for c in wanted_cards:
                            p["collection"].append(asdict(c))
                        for idx in sorted(target_indices, reverse=True):
                            enc.cards.pop(idx)
                        p["cash"] -= trade_cash

                        margin = target_value - offered_value
                        grant_xp_for_deal(enc.zone, margin, is_trade=True, is_sale=False)
                        enc.active = False
                    elif offered_value >= target_value * 0.7:
                        st.info("They think about it and counter higher.")
                        enc.history.append(
                            f"{enc.npc_type}: 'You’re close, but I’d need more to move these.'"
                        )
                        enc.price_factor += 0.05
                        enc.npc_hp = min(enc.npc_max_hp, enc.npc_hp + 10)
                    else:
                        st.warning("They decline the trade and seem unimpressed.")
                        enc.history.append(
                            f"{enc.npc_type}: 'That trade’s not even close.' (They get tougher.)"
                        )
                        enc.npc_hp = min(enc.npc_max_hp, enc.npc_hp + 15)
                        enc.patience -= 1
                        if enc.patience <= 0:
                            enc.active = False
                            enc.history.append(f"{enc.npc_type} has had enough and walks away.")

            st.markdown("### Sell to this dealer")

            if collection:
                sell_labels = [
                    f"{i}. {c['name']} ({c['set_name']} {c['year']}) – est ${c['true_value']:.2f}"
                    for i, c in enumerate(collection)
                ]
                sell_indices = st.multiselect(
                    "Cards you want to sell",
                    options=list(range(len(collection))),
                    format_func=lambda i: sell_labels[i],
                    key="sell_cards",
                )
            else:
                sell_indices = []

            sell_btn = st.button("Get cash offer for selected")

            if sell_btn and enc.active:
                if not sell_indices:
                    st.warning("Pick at least one card to get an offer.")
                else:
                    cards_to_sell = [collection[i] for i in sell_indices]
                    total_true_sell = sum(c["true_value"] for c in cards_to_sell)

                    base_buy_pct = {
                        "Dealer": 0.65,
                        "Flipper": 0.6,
                        "Kid Collector": 0.7,
                        "PC Supercollector": 0.75,
                    }.get(enc.npc_type, 0.65)

                    mood_adj = {"happy": 0.05, "neutral": 0.0, "grumpy": -0.05}[enc.mood]
                    zone_adj = {
                        "Dollar Boxes": -0.05,
                        "Trade Night": 0.05,
                    }.get(enc.zone, 0.0)

                    buy_pct = max(0.4, min(0.9, base_buy_pct + mood_adj + zone_adj))
                    offer_cash = round(total_true_sell * buy_pct, 2)

                    enc.history.append(
                        f"{enc.npc_type} offers ${offer_cash:.2f} for "
                        f"{len(cards_to_sell)} of your card(s) "
                        f"(est value ${total_true_sell:.2f})."
                    )
                    st.info(f"They offer you ${offer_cash:.2f} for your cards.")

                    if st.button("Accept sale", key="confirm_sale"):
                        for idx in sorted(sell_indices, reverse=True):
                            p["collection"].pop(idx)

                        p["cash"] += offer_cash
                        margin = offer_cash - total_true_sell
                        grant_xp_for_deal(enc.zone, margin, is_trade=False, is_sale=True)
                        enc.history.append(
                            f"You sell {len(cards_to_sell)} card(s) for ${offer_cash:.2f}."
                        )

            if walk and enc.active:
                enc.history.append("You walk away from the table.")
                enc.active = False
                st.write("You leave this dealer and head back to the floor.")

elif page == "Big Stages & Legends":
    st.title("Big Stages & Legends")

    if not p["build_locked"]:
        st.warning("Head to 'Intro & Build' first to roll your collector build.")
    else:
        st.subheader("Major Tables (big deals)")

        for gym in GYMS:
            has = has_big_deal(gym["id"])
            unlocked = p["level"] >= gym["required_level"]
            status = "✅ Big deal done" if has else (
                "🔓 Ready" if unlocked else f"🔒 Requires level {gym['required_level']}"
            )
            st.markdown(f"**{gym['name']}** – {gym['boss']}  |  {status}")
            st.caption(gym["description"])
            if unlocked and not has:
                if st.button(f"Sit down with {gym['boss']}", key=f"stage_{gym['id']}"):
                    start_stage_battle(gym["id"])
                    st.success(f"You sit down at {gym['name']}! Go to the Encounter page.")

        st.divider()
        st.subheader("Influencer Battles")

        for elite in ELITE_FOUR:
            has = elite["id"] in p["elite_defeated"]
            unlocked = p["level"] >= elite["required_level"] and len(p["badges"]) >= len(GYMS)
            status = "✅ Out‑negotiated" if has else (
                "🔓 Ready" if unlocked else f"🔒 Requires level {elite['required_level']} + all big deals"
            )
            st.markdown(f"**{elite['name']}** – {elite['boss']}  |  {status}")
            st.caption(elite["description"])
            if unlocked and not has:
                if st.button(f"Go on stream with {elite['boss']}", key=f"influencer_{elite['id']}"):
                    start_influencer_battle(elite["id"])
                    st.success(f"You’re live with {elite['boss']}! Go to the Encounter page.")

        st.divider()
        st.subheader("The National Whale")

        champ_unlocked = len(p["elite_defeated"]) >= len(ELITE_FOUR)
        champ_done = p["champion_defeated"]
        status = "✅ Deal done with the Whale" if champ_done else (
            "🔓 Ready" if champ_unlocked else "🔒 Out‑negotiate all four influencers first"
        )
        st.markdown(f"**{CHAMPION['name']}** – {CHAMPION['boss']}  |  {status}")
        st.caption(CHAMPION["description"])
        if champ_unlocked and not champ_done:
            if st.button("Approach the National Whale"):
                start_whale_battle()
                st.success("You approach the National Whale! Go to the Encounter page.")

elif page == "Collection & Results":
    st.title("Collection & Trip Results")

    st.subheader("Collection")
    if p["collection"]:
        st.table(p["collection"])
    else:
        st.write("You haven't picked up any cards yet.")

    st.divider()

    st.subheader("Trip summary")
    st.write(f"Trip profit (estimated): ${p['profit']:.2f}")
    st.write(f"Level: {p['level']}  |  XP: {p['xp']}")
    st.write(f"Big deals closed: {len(p['badges'])} / {len(GYMS)}")
    st.write(f"Influencers out‑negotiated: {len(p['elite_defeated'])} / {len(ELITE_FOUR)}")
    st.write(f"National Whale beaten: {'Yes' if p['champion_defeated'] else 'No'}")

    hit_pc = any(
        p["goals"]["target_pc_card"]
        and p["goals"]["target_pc_card"].lower() in c["name"].lower()
        for c in p["collection"]
    )

    if p["profit"] >= p["goals"]["profit_target"]:
        st.success("You hit your profit target for the trip!")
    else:
        remaining = p["goals"]["profit_target"] - p["profit"]
        st.info(f"You need ${remaining:.2f} more profit to hit your target.")

    if p["goals"]["target_pc_card"]:
        if hit_pc:
            st.success("You found something that fits your PC goal. Story-worthy pickup achieved.")
        else:
            st.info("You might still be chasing that perfect PC card—but the hunt continues.")
