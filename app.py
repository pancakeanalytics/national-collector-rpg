import streamlit as st
import random
from dataclasses import dataclass, asdict
from typing import List, Optional

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

BUILD_SUMMARY = {
    "Budget Grinder": (
        "The Spreadsheet Warrior",
        "You plan every show like a spreadsheet: budget dialed in, comps memorized, and a firm rule that the hobby must fund itself. "
        "You’re here to cover the trip and sneak in a smart PC upgrade."
    ),
    "PC Diehard": (
        "The True Believer",
        "You’re obsessed with one story told in cardboard: your player, your team, your era. "
        "Profit is nice, but the real win is going home saying, “I finally found it.”"
    ),
    "Flipper-in-Training": (
        "The Hustle Apprentice",
        "You see the hobby as a living market. You chase comps, edges, and arbitrage, dreaming of turning a small case into a big story. "
        "You’ll learn that face-to-face deals hit different than online listings."
    ),
}

# ---------- Big stages / “gym” equivalents ----------

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
        "archetype": None,
        "cash": 0.0,
        "stamina": 100,
        "negotiation_skill": 1.0,
        "day": 1,
        "time_block": "Morning",
        "xp": 0,
        "level": 1,
        "goals": {
            "target_pc_card": "",
            "profit_target": 0.0,
        },
        "collection": [],
        "profit": 0.0,
        "build_locked": False,
        "badges": [],
        "elite_defeated": [],
        "champion_defeated": False,
    }


def init_state():
    st.session_state.player = base_player_state()
    st.session_state.encounter: Optional[Encounter] = None


def roll_collector_build():
    player = st.session_state.player
    archetype = random.choice(["Budget Grinder", "PC Diehard", "Flipper-in-Training"])

    if archetype == "Budget Grinder":
        cash = 1500.0
        negotiation_skill = 0.8
        profit_target = 400.0
    elif archetype == "PC Diehard":
        cash = 800.0
        negotiation_skill = 1.0
        profit_target = 200.0
    else:
        cash = 1000.0
        negotiation_skill = 1.4
        profit_target = 600.0

    player["archetype"] = archetype
    player["cash"] = cash
    player["negotiation_skill"] = negotiation_skill
    player["goals"]["profit_target"] = profit_target
    if not player["goals"]["target_pc_card"]:
        player["goals"]["target_pc_card"] = (
            f"Grail for {player['favorite']}" if player["favorite"] else "A true PC grail"
        )
    player["build_locked"] = True


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


def grant_xp_for_deal(zone: str, margin: float, is_trade: bool, is_sale: bool = False):
    base = 5

    zone_factor = {
        "Dollar Boxes": 0.8,
        "Vintage Alley": 1.3,
        "Modern Showcases": 1.1,
        "Corporate Pavilion": 1.0,
        "Trade Night": 1.2,
    }.get(zone, 1.0)

    margin_xp = max(0.0, margin / 20.0)
    margin_xp = min(margin_xp, 40.0)

    trade_bonus = 1.3 if is_trade else 1.0
    if is_sale:
        trade_bonus = 0.9

    total_xp = int((base + margin_xp) * zone_factor * trade_bonus)
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
    skill = player["negotiation_skill"]

    behavior = NPC_BEHAVIOR.get(enc.npc_type, {"min_pct": 0.85})
    base_min_pct = behavior["min_pct"]

    mood_factor = {
        "happy": base_min_pct - 0.05,
        "neutral": base_min_pct,
        "grumpy": base_min_pct + 0.05,
    }[enc.mood]

    if player["archetype"] == "Budget Grinder" and enc.zone == "Dollar Boxes":
        mood_factor -= 0.03
    if player["archetype"] == "Flipper-in-Training" and enc.npc_type in ["Dealer", "Flipper"]:
        mood_factor -= 0.03

    hp_factor = max(0.5, enc.npc_hp / enc.npc_max_hp)
    effective_min_pct = mood_factor * enc.price_factor * hp_factor

    skill_discount = 0.03 * (skill - 1)
    threshold = total_true * max(0.6, effective_min_pct - skill_discount)

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

    player["negotiation_skill"] = min(5.0, player["negotiation_skill"] + 0.1)
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

    hp_delta = 0
    price_delta = 0.0
    patience_delta = 0
    line = ""

    if move == "friendly_chat":
        if npc in ["Kid Collector", "PC Supercollector"]:
            hp_delta = -15
            line = f"{npc}: 'Haha, love talking cards. I can work with you a bit.' (Deal resistance drops.)"
        else:
            hp_delta = -5
            price_delta = 0.05
            line = f"{npc}: 'Sure, but let's not waste time.' (They nudge their ask up slightly.)"
    elif move == "point_flaws":
        if npc in ["Dealer", "Flipper"]:
            hp_delta = -20
            price_delta = -0.08
            line = f"{npc}: 'Fair point on the centering. I can come down some.' (Price softens.)"
        else:
            hp_delta = 10
            line = f"{npc}: 'Hey, I love this card—don't knock it.' (They get a bit defensive.)"
    elif move == "lowball_probe":
        if npc in ["Dealer", "Flipper"]:
            hp_delta = -10
            price_delta = 0.05
            patience_delta = -1
            line = f"{npc}: 'That's low, but now we’re talking numbers.' (They get a bit annoyed; ask creeps up.)"
        else:
            hp_delta = 15
            patience_delta = -2
            line = f"{npc}: 'That feels disrespectful.' (They might walk sooner.)"
    elif move == "show_comp":
        hp_delta = -12
        price_delta = -0.05
        line = f"{npc}: 'Okay, those comps are solid.' (Ask comes down a bit.)"

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

# ---------- Sidebar & page selection (Intro hidden after build) ----------

st.sidebar.title("Trip Status")
st.sidebar.write(f"Collector: {p['name'] or '—'}")
st.sidebar.write(f"Build: {p['archetype'] or '—'}")
st.sidebar.write(f"Day (chapter): {p['day']}")
st.sidebar.write(f"Time (flavor): {p['time_block']}")
st.sidebar.write(f"Level: {p['level']}  |  XP: {p['xp']}")
st.sidebar.write(f"Cash: ${p['cash']:.2f}")
st.sidebar.write(f"Stamina: {p['stamina']}")
st.sidebar.write(f"Negotiation Skill: {p['negotiation_skill']:.1f}")
st.sidebar.markdown("**Goals**")
st.sidebar.write(f"Target PC: {p['goals']['target_pc_card'] or '—'}")
st.sidebar.write(f"Profit target: ${p['goals']['profit_target']:.2f}")
st.sidebar.write(f"Trip profit: ${p['profit']:.2f}")
st.sidebar.markdown("**Milestones**")
st.sidebar.write(f"Big deals closed: {len(p['badges'])}")
st.sidebar.write(f"Influencers out‑negotiated: {len(p['elite_defeated'])}/4")
st.sidebar.write("National Whale beaten: ✅" if p["champion_defeated"] else "National Whale beaten: ❌")

if p["build_locked"]:
    page_options = ["Show Floor", "Encounter", "Big Stages & Legends", "Collection & Results"]
else:
    page_options = ["Intro & Build", "Show Floor", "Encounter", "Big Stages & Legends", "Collection & Results"]

page = st.sidebar.radio("Go to", page_options)

if not p["build_locked"]:
    page = "Intro & Build"

# ---------- Pages ----------

if page == "Intro & Build":
    st.title("National Collector RPG")

    st.image("001_image.png", use_column_width=True)
    st.markdown(
        "<p style='margin-top:0.3rem; color:#555;'>Turn your National trip into a story told in cardboard.</p>",
        unsafe_allow_html=True,
    )

    st.subheader("Intro & Build")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Collector name", value=p["name"])
    with col2:
        favorite = st.text_input("Favorite player or team", value=p["favorite"])

    target_pc = st.text_input(
        "Describe your dream PC pickup for this trip",
        value=p["goals"]["target_pc_card"],
    )

    st.write("When you start the trip, the game will randomly assign you a collector build with perks and flaws.")

    if st.button("Start trip / roll build", disabled=p["build_locked"] and p["archetype"]):
        p["name"] = name or "Unnamed Collector"
        p["favorite"] = favorite
        p["goals"]["target_pc_card"] = target_pc
        roll_collector_build()
        st.success("Build locked in! Scroll down to see who you are this trip.")

    if p["archetype"]:
        title, summary = BUILD_SUMMARY[p["archetype"]]
        st.divider()
        st.markdown(
            f"""
            <div style="
                padding:0.9rem 1.1rem;
                background-color:#ffffff;
                border-radius:0.9rem;
                border:2px solid #e0e0ff;
                box-shadow:0 2px 6px rgba(0,0,0,0.04);
                margin-bottom:0.8rem;">
                <p style="margin:0.1rem 0; color:#777;">
                    Welcome, <b>{p['name']}</b>. Fate dealt you:
                </p>
                <p style="margin:0.15rem 0; font-weight:600;">
                    {p['archetype']} – <span style="color:#e63946;">{title}</span>
                </p>
                <p style="margin:0.15rem 0;">
                    {summary}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

                    buy_pct = max(0.4, min(0.9, base_buy_pct + mood_a
