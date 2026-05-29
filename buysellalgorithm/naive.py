def naivealgo(pv_p, demand, deferrable, vbus, energy_cap, tick):
    if pv_p > demand:
        power_left = pv_p - demand
        for d in sorted(deferrable, key=lambda x: x['tick_end']):
            if power_left > 0 and d['energy'] > 0 and d['tick_start'] <= tick <= d['tick_end']:
                if d['energy'] <= power_left:
                    power_left -= d['energy']
                    d['energy'] = 0
                else:
                    d['energy'] -= power_left
                    power_left = 0
        p_grn = p_red = p_yel = (pv_p - power_left) / 3
        if power_left > 0:
            i_cap = power_left / vbus
            return i_cap
    elif energy_cap > 0:
        p_grn = p_red = p_yel = demand / 3
        return -0.3
    return 0.0