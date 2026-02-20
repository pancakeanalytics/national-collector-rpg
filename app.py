import streamlit as st
import random
from dataclasses import dataclass, asdict
from typing import List, Optional

# ---------- Page config & global CSS ----------

st.set_page_config(page_title="National Collector RPG", layout="wide")

st.markdown(
    """
    <style>
    /* Soft gradient app background */
    .stApp {
        background-image: radial-gradient(circle at top left, #ffffff 0, #f7f7ff 50%, #f0f0ff 100%);
    }
    /* Table zebra striping, subtle */
    .stTable tbody tr:nth-child(even) {
        background-color: #fafaff;
    }
    .stTable th {
        background-color: #f0f0ff !important;
    }
    /* Pill-like primary buttons */
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
    true_value: float  # internal market value
    ask_price: float   # NPC initial ask


@dataclass
class Encounter:
    npc_type: str
    mood: str
    zone: str
    cards: List[Card]
    round: int
    active: bool
    history: List[str]


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


# ---------- Game helpers ----------

def init_state():
    st.session_state.player = {
        "cash": 1000.0,
        "stamina": 100,
        "negotiation_skill": 1.0,  # 1–5
        "day": 1,
        "time_block": "Morning",  # Morning / Afternoon / Evening
        "goals": {
            "target_pc_card": "Star QB Rookie",
            "profit_target": 300.0,
        },
        "collection": [],
        "profit": 0.0,
    }
    st.session_state.encounter: Optional[Encounter] = None


def advance_time(cost_stamina=10):
    """Advance time within the day and drain stamina."""
    time_order = ["Morning", "Afternoon", "Evening"]
    player = st.session_state.player
    idx = time_order.index(player["time_block"])
    player["stamina"] = max(0, player["stamina"] - cost_stamina)
    if idx < len(time_order) - 1:
        player["time_block"] = time_order[idx + 1]
    else:
        player["day"] += 1
        player["time_block"] = "Morning"
        player["stamina"] = 100


def generate_cards_for_zone(zone: str, npc_type: str) -> List[Card]:
    """Zone + NPC-based card generator."""
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
    else:  # Trade Night
        base_cards = [
            ("PC Parallel", "Your PC Guy", 2019, "Optic", 80.0),
            ("Random RC", "Random Rookie", 2021, "Mosaic", 25.0),
        ]

    behavior = NPC_BEHAVIOR.get(npc_type, {"overask": (1.1, 1.4)})
    lo, hi = behavior["overask"]

    cards = []
    for name, player, year, set_name, true_value in base_cards:
        ask = round(true_value * random.uniform(lo, hi), 2)
        cards.append(Card(name, player, year, set_name, true_value, ask))
    return cards


def start_encounter(zone: str):
    npc_type = random.choice(NPC_TYPES)
    mood = random.choice(MOODS)
    cards = generate_cards_for_zone(zone, npc_type)
    st.session_state.encounter = Encounter(
        npc_type=npc_type,
        mood=mood,
        zone=zone,
        cards=cards,
        round=1,
        active=True,
        history=[f"You approach a {npc_type} in {zone}. They seem {mood}."],
    )
    advance_time(cost_stamina=5)


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

    skill_discount = 0.03 * (skill - 1)
    threshold = total_true * max(0.6, mood_factor - skill_discount)

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


def pick_trade_card():
    """Pick a random card from player's collection, if any."""
    coll = st.session_state.player["collection"]
    if not coll:
        return None
    return random.choice(coll)


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


# ---------- Sidebar (status) ----------

p = st.session_state.player

st.sidebar.title("Trip Status")
st.sidebar.write(f"Day: {p['day']}")
st.sidebar.write(f"Time: {p['time_block']}")
st.sidebar.write(f"Cash: ${p['cash']:.2f}")
st.sidebar.write(f"Stamina: {p['stamina']}")
st.sidebar.write(f"Negotiation Skill: {p['negotiation_skill']:.1f}")
st.sidebar.markdown("**Goals**")
st.sidebar.write(f"Target PC Card: {p['goals']['target_pc_card']}")
st.sidebar.write(f"Profit target: ${p['goals']['profit_target']:.2f}")
st.sidebar.write(f"Trip profit: ${p['profit']:.2f}")


# ---------- Navigation ----------

page = st.sidebar.radio(
    "Go to",
    ["Prep & Goals", "Show Floor", "Encounter", "Collection & Results"],
)


# ---------- Pages ----------

if page == "Prep & Goals":
    st.title("Prep & Goals")
    st.write("Set up your trip goals before diving into The National.")

    col1, col2 = st.columns(2)
    with col1:
        target_card = st.text_input(
            "Target PC card description",
            p["goals"]["target_pc_card"],
        )
    with col2:
        profit_target = st.number_input(
            "Profit target for the trip",
            0.0, 10000.0, p["goals"]["profit_target"], step=50.0,
        )

    if st.button("Update goals"):
        p["goals"]["target_pc_card"] = target_card
        p["goals"]["profit_target"] = profit_target
        st.success("Goals updated!")

    st.divider()
    st.markdown(
        "Tip: Plan a couple of grails and a realistic flip target, just like prepping for the real National."
    )

elif page == "Show Floor":
    st.title("Show Floor")
    st.write("Choose where to head next at The National.")

    if p["stamina"] <= 0:
        st.warning("You are exhausted. Advancing to the next day...")
        advance_time(cost_stamina=0)

    st.markdown("#### Zones")

    for name in ZONES:
        meta = ZONE_META[name]
        st.markdown(
            f"""
            <div style="
                padding:0.55rem 0.8rem;
                margin-bottom:0.4rem;
                border-radius:0.6rem;
                border:1px solid #e0e0ff;
                background-color:#ffffff;">
                <span style="font-size:1.1rem; margin-right:0.35rem;">{meta['icon']}</span>
                <span style="font-weight:600;">{name}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    zone = st.selectbox("Where do you want to go?", ZONES)

    if st.button("Walk to this zone"):
        start_encounter(zone)
        st.success(f"You walk over to {zone} and spot a potential deal.")
        st.info("Switch to the 'Encounter' page to negotiate.")

elif page == "Encounter":
    st.title("Encounter")

    enc: Encounter = st.session_state.encounter

    if enc is None or not enc.active:
        st.write("No active encounter. Head to the Show Floor to find a deal.")
    else:
        zone_meta = ZONE_META.get(enc.zone, {"icon": "🎪"})
        npc_meta = NPC_META.get(enc.npc_type, {"icon": "🙂"})

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
                    Day {p['day']} • {p['time_block']} • {zone_meta['icon']} {enc.zone}
                </p>
                <p style="margin:0.15rem 0; font-weight:600;">
                    {npc_meta['icon']} A <span style="color:#e63946;">{enc.npc_type}</span> appears. They seem <b>{enc.mood}</b>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Recent conversation")
        for line in enc.history[-5:]:
            st.write("•", line)

        left, right = st.columns([2, 1], gap="medium")

        with left:
            st.markdown("#### Cards on the table")
            st.table(
                [
                    {
                        "Card": c.name,
                        "Player": c.player,
                        "Year": c.year,
                        "Set": c.set_name,
                        "Ask ($)": c.ask_price,
                    }
                    for c in enc.cards
                ]
            )

        with right:
            st.markdown("#### Your move")
            total_ask = sum(c.ask_price for c in enc.cards)
            offer = st.number_input(
                "Cash offer",
                0.0, 10000.0, min(total_ask, p["cash"]), step=5.0,
            )

            btn_row = st.columns(4, gap="small")
            make_offer = btn_row[0].button("Make offer")
            sweeten = btn_row[1].button("Talk comps")
            trade_btn = btn_row[2].button("Offer trade")
            walk = btn_row[3].button("Walk away")

            if make_offer:
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
                        advance_time(cost_stamina=3)

            if sweeten:
                st.info("You reference comps and build rapport. They soften a bit.")
                if enc.mood == "grumpy":
                    enc.mood = "neutral"
                enc.history.append("You talk comps; they seem slightly more open.")
                advance_time(cost_stamina=2)

            if trade_btn:
                trade_card = pick_trade_card()
                if not trade_card:
                    st.warning("You don't have anything in your case yet to trade.")
                else:
                    target_card = random.choice(enc.cards)
                    enc.history.append(
                        f"You offer your {trade_card['name']} for their {target_card.name}."
                    )
                    if trade_card["true_value"] >= target_card.true_value * 0.9:
                        st.success("They like the trade and accept!")
                        st.session_state.player["collection"].remove(trade_card)
                        st.session_state.player["collection"].append(asdict(target_card))
                        enc.active = False
                    else:
                        st.warning("They decline the trade. Maybe sweeten the deal or add cash.")
                        enc.round += 1

            if walk:
                enc.history.append("You walk away from the table.")
                enc.active = False
                advance_time(cost_stamina=1)
                st.write("You leave this dealer and head back to the floor.")

elif page == "Collection & Results":
    st.title("Collection & Trip Results")
    st.write("See what you picked up and how your trip is going.")

    st.subheader("Collection")
    if p["collection"]:
        st.table(p["collection"])
    else:
        st.write("You haven't picked up any cards yet.")

    st.divider()

    st.subheader("Trip summary")
    st.write(f"Trip profit (estimated): ${p['profit']:.2f}")
    st.write(f"Negotiation skill: {p['negotiation_skill']:.1f}")

    if p["profit"] >= p["goals"]["profit_target"]:
        st.success("You hit your profit target for the trip!")
    else:
        remaining = p["goals"]["profit_target"] - p["profit"]
        st.info(f"You need ${remaining:.2f} more profit to hit your target.")
