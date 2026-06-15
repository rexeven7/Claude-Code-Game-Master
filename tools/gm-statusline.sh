#!/usr/bin/env bash
# gm-statusline.sh - Forbidden Lands HUD for Claude Code.
#
# Shows four FL attribute bars (STR/AGI/WIT/EMP), conditions, AR, WP, XP, and
# world time. Uses Python for JSON parsing (jq not required).

input=$(cat)   # Claude Code JSON payload on stdin (unused)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GREEN=$'\033[38;5;42m'
AMBER=$'\033[38;5;214m'
RED=$'\033[38;5;203m'
TEAL=$'\033[38;5;51m'
GOLD=$'\033[38;5;220m'
DIM=$'\033[38;5;244m'
FAINT=$'\033[38;5;238m'
BOLD=$'\033[1m'
RESET=$'\033[0m'
SEP="${DIM}*${RESET}"
SEPV="${FAINT}|${RESET}"

divider() {
    local rule="${1:-$FAINT}" orn="${2:-$TEAL}"
    local cols mid half left right
    cols=$(tput cols 2>/dev/null)
    case "$cols" in ''|*[!0-9]*) cols=80 ;; esac
    [ "$cols" -gt 120 ] && cols=120
    [ "$cols" -lt 24  ] && cols=24
    mid="+"
    half=$(( (cols - 1) / 2 ))
    printf -v left  '%*s' "$half" '';            left="${left// /-}"
    printf -v right '%*s' "$(( cols - 1 - half ))" ''; right="${right// /-}"
    printf '%s%s%s%s%s%s%s\n' "$rule" "$left" "$orn" "$mid" "$rule" "$right" "$RESET"
}

ACTIVE_FILE="$ROOT/world-state/active-campaign.txt"
if [ ! -f "$ACTIVE_FILE" ] || [ ! -s "$ACTIVE_FILE" ]; then
    divider
    printf '%s[GM]%s  %sno campaign%s  %s  type %s/gm%s to begin\n' \
        "$TEAL$BOLD" "$RESET" "$DIM" "$RESET" "$SEP" "$TEAL$BOLD" "$RESET"
    divider
    exit 0
fi
ACTIVE=$(tr -d '[:space:]' < "$ACTIVE_FILE")
CAMP="$ROOT/world-state/campaigns/$ACTIVE"
CHAR="$CAMP/character.json"
OVER="$CAMP/campaign-overview.json"

if [ ! -f "$CHAR" ]; then
    divider
    printf '%s[GM]%s  %s%s%s  %sno character%s  %s  type %s/gm%s to begin\n' \
        "$TEAL$BOLD" "$RESET" "$BOLD" "$ACTIVE" "$RESET" "$DIM" "$RESET" "$SEP" "$TEAL$BOLD" "$RESET"
    divider
    exit 0
fi

# Parse character + overview with Python (no jq needed)
PARSE=$(PYTHONIOENCODING=utf-8 uv run python3 - "$CHAR" "$OVER" 2>/dev/null <<'PYEOF'
import json, sys

char_f = sys.argv[1]
over_f = sys.argv[2] if len(sys.argv) > 2 else None

with open(char_f, encoding='utf-8') as f:
    c = json.load(f)

attr = c.get('attributes', {})
str_max = int(attr.get('strength', c.get('stats', {}).get('str', 2)))
agi_max = int(attr.get('agility', c.get('stats', {}).get('dex', 4)))
wit_max = int(attr.get('wits', c.get('stats', {}).get('con', 5)))
emp_max = int(attr.get('empathy', c.get('stats', {}).get('cha', 3)))

# Current values — fall back to max if not tracked separately
cur = c.get('current_attributes', {})
str_cur = int(cur.get('strength', str_max))
agi_cur = int(cur.get('agility', agi_max))
wit_cur = int(cur.get('wits', wit_max))
emp_cur = int(cur.get('empathy', emp_max))

# If hp.max matches str_max, use hp.current as live STR (legacy compat)
hp = c.get('hp', {})
if isinstance(hp, dict) and int(hp.get('max', -1)) == str_max:
    str_cur = int(hp.get('current', str_cur))

wp = c.get('willpower', {})
wp_cur = int(wp.get('current', 0)) if isinstance(wp, dict) else 0
wp_max = int(wp.get('max', 10)) if isinstance(wp, dict) else 10

gold = int(c.get('gold', 0))
xp_val = c.get('xp', {})
xp_cur = int(xp_val.get('current', 0)) if isinstance(xp_val, dict) else 0

ar = int(c.get('ac', 0))
name = c.get('name', '?')
race = c.get('race', '?')
cls  = c.get('class', '?')

conds_raw = [x.lower() for x in c.get('conditions', [])]
hungry  = 'X' if 'hungry'  in conds_raw else '_'
thirsty = 'X' if 'thirsty' in conds_raw else '_'
sleepy  = 'X' if 'sleepy'  in conds_raw else '_'
cold    = 'X' if 'cold'    in conds_raw else '_'

loc = '?'; date = ''; tod = ''
if over_f:
    try:
        with open(over_f, encoding='utf-8') as f:
            o = json.load(f)
        date = o.get('current_date', '')
        tod  = o.get('time_of_day', '')
        oloc = o.get('player_position', {}).get('current_location', '')
        if oloc: loc = oloc
    except Exception:
        pass

print('\t'.join(str(x) for x in [
    name, race, cls,
    str_cur, str_max, agi_cur, agi_max, wit_cur, wit_max, emp_cur, emp_max,
    wp_cur, wp_max, ar, gold, xp_cur,
    hungry, thirsty, sleepy, cold,
    loc, date, tod
]))
PYEOF
)

if [ -z "$PARSE" ]; then
    divider
    printf '%s[GM]%s  %s%s%s  %sparse error%s\n' \
        "$TEAL$BOLD" "$RESET" "$BOLD" "$ACTIVE" "$RESET" "$RED" "$RESET"
    divider
    exit 0
fi

IFS=$'\t' read -r NAME RACE CLASS \
    STR_CUR STR_MAX AGI_CUR AGI_MAX WIT_CUR WIT_MAX EMP_CUR EMP_MAX \
    WP_CUR WP_MAX AR GP XP \
    HUNGRY THIRSTY SLEEPY COLD \
    LOC DATE TOD <<< "$PARSE"

# Build attribute bar (filled=█ empty=░, length = attribute max)
make_bar() {
    local cur=$1 max=$2 bar="" i
    local filled=$(printf '\xe2\x96\x88')  # █
    local empty=$(printf '\xe2\x96\x91')   # ░
    for ((i=1; i<=max; i++)); do
        if [ "$i" -le "$cur" ] 2>/dev/null; then bar="${bar}${filled}"; else bar="${bar}${empty}"; fi
    done
    printf '%s' "$bar"
}

# Attribute color: green=full, amber=damaged, red=broken
attr_color() {
    local cur=$1 max=$2
    if   [ "$cur" -le 0 ] 2>/dev/null;                                 then printf '%s' "$RED"
    elif [ "$cur" -lt "$max" ] 2>/dev/null;                            then printf '%s' "$AMBER"
    else                                                                     printf '%s' "$GREEN"
    fi
}

# Frame color: red if anything broken, amber if anything damaged, calm otherwise
RULEC="$FAINT"; ORNC="$TEAL"
for pair in "$STR_CUR:$STR_MAX" "$AGI_CUR:$AGI_MAX" "$WIT_CUR:$WIT_MAX" "$EMP_CUR:$EMP_MAX"; do
    cur="${pair%%:*}"; max="${pair##*:}"
    [ "$cur" -le 0 ] 2>/dev/null && { RULEC="${BOLD}${RED}"; ORNC="${BOLD}${RED}"; break; }
    [ "$cur" -lt "$max" ] 2>/dev/null && { RULEC="$AMBER"; ORNC="$AMBER"; }
done

# Condition display: [_] inactive, [X] active
cond_str="[${HUNGRY}]Hungry [${THIRSTY}]Thirsty [${SLEEPY}]Sleepy [${COLD}]Cold"
[ "$HUNGRY$THIRSTY$SLEEPY$COLD" != "____" ] && COND_COLOR="$AMBER" || COND_COLOR="$DIM"

# --- Render ---
divider "$RULEC" "$ORNC"

# Line 1: identity + location
printf '%s[%s]%s  %s%s%s  %s%s %s%s  %s  %s%s%s\n' \
    "$TEAL$BOLD" "GM" "$RESET" \
    "$BOLD" "$NAME" "$RESET" \
    "$DIM" "$RACE" "$CLASS" "$RESET" \
    "$SEP" \
    "$AMBER" "$LOC" "$RESET"

# Line 2: attribute bars
SC=$(attr_color "$STR_CUR" "$STR_MAX"); SB=$(make_bar "$STR_CUR" "$STR_MAX")
AC=$(attr_color "$AGI_CUR" "$AGI_MAX"); AB=$(make_bar "$AGI_CUR" "$AGI_MAX")
WC=$(attr_color "$WIT_CUR" "$WIT_MAX"); WB=$(make_bar "$WIT_CUR" "$WIT_MAX")
EC=$(attr_color "$EMP_CUR" "$EMP_MAX"); EB=$(make_bar "$EMP_CUR" "$EMP_MAX")

printf '  %sSTR%s %s%s%s %s/%s  %sAGI%s %s%s%s %s/%s  %sWIT%s %s%s%s %s/%s  %sEMP%s %s%s%s %s/%s  %s  %sAR%s %s  %s  %sWP%s %s/%s  %s  %s%sgp%s  %s  %sXP%s %s\n' \
    "$DIM" "$RESET" "$SC" "$SB" "$RESET" "$STR_CUR" "$STR_MAX" \
    "$DIM" "$RESET" "$AC" "$AB" "$RESET" "$AGI_CUR" "$AGI_MAX" \
    "$DIM" "$RESET" "$WC" "$WB" "$RESET" "$WIT_CUR" "$WIT_MAX" \
    "$DIM" "$RESET" "$EC" "$EB" "$RESET" "$EMP_CUR" "$EMP_MAX" \
    "$SEPV" \
    "$DIM" "$RESET" "$AR" \
    "$SEPV" \
    "$DIM" "$RESET" "$WP_CUR" "$WP_MAX" \
    "$SEPV" \
    "$GOLD" "$GP" "$RESET" \
    "$SEPV" \
    "$DIM" "$RESET" "$XP"

# Line 3: conditions + world time
if [ -n "$DATE" ] || [ -n "$TOD" ]; then
    printf '  %s%s%s  %s  %s%s %s %s%s\n' \
        "$COND_COLOR" "$cond_str" "$RESET" \
        "$SEP" \
        "$DIM" "$TOD" "$SEP" "$DATE" "$RESET"
else
    printf '  %s%s%s\n' "$COND_COLOR" "$cond_str" "$RESET"
fi

divider "$RULEC" "$ORNC"
