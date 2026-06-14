import streamlit as st
from src.blue_table_tools import calculate_single_option_premium

def render_step2(setup: dict, config: dict) -> None:
    st.subheader("🎨 Step 2: Interactive Plan & Premium Sandbox")
    st.write("Input family structure (static params) and customize Option A, B, and C (dynamic params) to compare them side-by-side.")

    col_setup, col_pricing = st.columns([1.5, 3.5], gap="large")

    with col_setup:
        st.subheader("👨‍👩‍👧 Static Parameters: Family Structure")

        setup["main_age"] = st.number_input("Main Insured Age", min_value=0, max_value=64, value=setup["main_age"])

        setup["cover_spouse"] = st.checkbox("Cover Spouse", value=setup["cover_spouse"])
        if setup["cover_spouse"]:
            setup["spouse_age"] = st.number_input("Spouse Age", min_value=18, max_value=64, value=setup["spouse_age"])

        setup["child_count"] = st.slider("Number of Children to Cover", min_value=0, max_value=3, value=setup["child_count"])

        for i in range(1, setup["child_count"] + 1):
            setup[f"child_{i}_age"] = st.number_input(f"Child {i} Age", min_value=0, max_value=17, value=setup.get(f"child_{i}_age", 10))

    with col_pricing:
        st.subheader("🏷️ Dynamic Parameters: Compare Custom Options")
        st.write("Configure each column independently to compare plan level, coverage, and deductible combinations.")

        coverage_labels = {
            "ipd": "IPD Only",
            "ipd_opd_3000": "IPD + OPD 3,000 THB/visit (30 visits/year)",
            "ipd_opd_3000_wellness": "IPD + OPD 3,000 THB + Wellness",
            "ipd_opd_50000": "IPD + OPD 50,000 THB/year",
            "ipd_opd_50000_wellness": "IPD + OPD 50,000 THB + Wellness"
        }

        deductibles = config.get("pricing", {}).get("deductibles", [])
        ded_labels = {d["key"]: d["label"] for d in deductibles}

        st.markdown("### **➕ Add Custom Combination to Compare**")
        col_new_plan, col_new_cov, col_new_ded = st.columns(3)
        with col_new_plan:
            new_plan = st.selectbox(
                "Select Plan",
                ["Plan 1", "Plan 2", "Plan 3", "Plan 4"],
                key="new_plan_sel"
            )
        with col_new_cov:
            new_coverage = st.selectbox(
                "Select Coverage",
                list(coverage_labels.keys()),
                format_func=lambda x: coverage_labels[x],
                key="new_cov_sel"
            )
        with col_new_ded:
            new_ded = st.selectbox(
                "Select Deductible",
                list(ded_labels.keys()),
                format_func=lambda x: ded_labels[x],
                key="new_ded_sel"
            )

        if st.button("➕ Add to Comparison", use_container_width=True):
            options = setup.setdefault("comparison_options", [])
            setup["option_counter"] = setup.get("option_counter", len(options)) + 1
            new_id = setup["option_counter"]

            exists = any(
                o["plan"] == new_plan and o["coverage"] == new_coverage and o["deductible"] == new_ded
                for o in options
            )
            if exists:
                st.warning("⚠️ This combination is already in the comparison.")
            else:
                options.append({
                    "id": new_id,
                    "name": f"Option {new_id}",
                    "plan": new_plan,
                    "coverage": new_coverage,
                    "deductible": new_ded
                })
                if "selected_option_id" not in setup or not any(o["id"] == setup["selected_option_id"] for o in options):
                    setup["selected_option_id"] = new_id
                st.rerun()

        options = setup.get("comparison_options", [])
        if not options:
            options = [
                {"id": 1, "name": "Option 1", "plan": "Plan 1", "coverage": "ipd", "deductible": "0"},
                {"id": 2, "name": "Option 2", "plan": "Plan 2", "coverage": "ipd_opd_3000", "deductible": "0"},
                {"id": 3, "name": "Option 3", "plan": "Plan 3", "coverage": "ipd_opd_50000", "deductible": "20000"}
            ]
            setup["comparison_options"] = options
            setup["selected_option_id"] = 2
            setup["option_counter"] = 3

        st.divider()
        st.subheader("📊 Comparison Matrix")

        options_data = []
        for opt in options:
            res = calculate_single_option_premium(opt["plan"], opt["coverage"], int(opt["deductible"]), setup, config)
            options_data.append({
                "id": opt["id"],
                "name": opt["name"],
                "plan": opt["plan"],
                "coverage": opt["coverage"],
                "deductible": opt["deductible"],
                "res": res
            })

        h1 = "| Parameter / Option |"
        h2 = "| :--- |"

        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            header = f"**{opt['name']} (Selected) ✅**" if is_sel else f"**{opt['name']}**"
            h1 += f" {header} |"
            h2 += " :---: |"

        r_plan = "| **Plan Tier** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['plan']}**" if is_sel else f"{opt['plan']}"
            r_plan += f" {val} |"

        r_cov = "| **Coverage Type** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            lbl = coverage_labels[opt["coverage"]]
            val = f"**{lbl}**" if is_sel else f"{lbl}"
            r_cov += f" {val} |"

        r_ded = "| **Deductible** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            lbl = ded_labels[opt["deductible"]]
            val = f"**{lbl}**" if is_sel else f"{lbl}"
            r_ded += f" {val} |"

        r_ipd = "| **IPD Limit** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['coverage']}**" if is_sel else f"{opt['res']['coverage']}"
            r_ipd += f" {val} |"

        r_room = "| **Room Limit** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['room_limit']} THB**" if is_sel else f"{opt['res']['room_limit']} THB"
            r_room += f" {val} |"

        r_tot = "| **Total Annual Premium** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['total']:,.0f} THB**" if is_sel else f"{opt['res']['total']:,.0f} THB"
            r_tot += f" {val} |"

        r_avg = "| **Average / Person** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['avg']:,.0f} THB**" if is_sel else f"{opt['res']['avg']:,.0f} THB"
            r_avg += f" {val} |"

        table_md = f"{h1}\n{h2}\n{r_plan}\n{r_cov}\n{r_ded}\n{r_ipd}\n{r_room}\n{r_tot}\n{r_avg}"
        st.markdown(table_md)

        st.markdown("🗑️ **Remove Options from Comparison:**")
        rem_cols = st.columns(max(len(options_data), 1))
        for idx, opt in enumerate(options_data):
            with rem_cols[idx]:
                if st.button(f"Remove {opt['name']} ❌", key=f"rem_opt_{opt['id']}", disabled=(len(options_data) <= 1)):
                    if setup.get("selected_option_id") == opt["id"]:
                        remaining = [o for o in options_data if o["id"] != opt["id"]]
                        setup["selected_option_id"] = remaining[0]["id"]
                    setup["comparison_options"] = [o for o in options if o["id"] != opt["id"]]
                    st.rerun()

        st.divider()
        st.subheader("Select Final Choice for Application")
        option_names = [o["name"] for o in options_data]
        selected_name = next((o["name"] for o in options_data if o["id"] == setup.get("selected_option_id")), option_names[0])
        selected_option = st.radio(
            "Apply Selected Combination",
            options=option_names,
            index=option_names.index(selected_name),
            horizontal=True
        )
        setup["selected_option_id"] = next(o["id"] for o in options_data if o["name"] == selected_option)

        o_count = 1 + (1 if setup["cover_spouse"] else 0) + setup["child_count"]
        if o_count >= 2 and o_count <= 3:
            st.info("🎉 Family Volume Discount: **5% off** has been automatically applied to all options.")
        elif o_count >= 4:
            st.info("🎉 Family Volume Discount: **10% off** has been automatically applied to all options.")

    st.markdown("---")

    col_b, col_n = st.columns([1, 1])
    with col_b:
        if st.button("⬅️ Back to Health Gate"):
            st.session_state.step = 1
            st.rerun()
    with col_n:
        if st.button("Proceed to Details Intake ➡️", type="primary", use_container_width=True):
            st.session_state.members_setup = setup

            chosen_opt = next(o for o in options_data if o["id"] == setup["selected_option_id"])

            st.session_state.form_data["plan"] = chosen_opt["plan"]
            st.session_state.form_data["deductible"] = ded_labels[chosen_opt["deductible"]]
            st.session_state.form_data["premium"] = f"{chosen_opt['res']['total']:,.0f}"
            st.session_state.step = 3
            st.rerun()
