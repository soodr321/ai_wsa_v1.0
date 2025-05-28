# fve_agent.py
import json
import re

class DCFAssumptionKeys:
    STAGE_1_GROWTH_PCT = "stage_1_fcfe_growth_rates_pct"; JUSTIFICATION_STAGE_1_GROWTH = "justification_stage_1_growth"
    PERPETUAL_GROWTH_G_PCT = "perpetual_growth_rate_g_pct"; JUSTIFICATION_PERPETUAL_GROWTH = "justification_perpetual_growth"
    COST_OF_EQUITY_KE_PCT = "cost_of_equity_ke_pct"; JUSTIFICATION_KE = "justification_ke"
    BETA_USED_IN_KE_CALC = "beta_used_in_ke_calc"
MIN_KE_G_SPREAD_DEFAULT = 0.005

class MultiplesAssumptionKeys:
    SELECTED_PE_VALUE = "selected_pe_multiple_value"; SELECTED_PE_TYPE = "selected_pe_multiple_type"
    JUSTIFICATION_PE = "justification_pe_multiple"; SELECTED_EPS_VALUE = "selected_eps_value"
    SELECTED_EPS_TYPE = "selected_eps_type"; JUSTIFICATION_EPS = "justification_eps_selection"

class FVEAgent:
    def __init__(self, llm_generate_text_func, rfr: float, erp: float, stage1_years: int, 
                 min_ke_g_spread: float = MIN_KE_G_SPREAD_DEFAULT, debug_mode: bool = False):
        self.llm_generate_text_func = llm_generate_text_func
        self.rfr = rfr; self.erp = erp; self.stage1_years = stage1_years
        self.min_ke_g_spread_decimal = min_ke_g_spread 
        self.min_ke_g_spread_pct = self.min_ke_g_spread_decimal * 100
        self.debug_mode = debug_mode
        self._reset_internal_state()

    def _reset_internal_state(self):
        self.fve_input_data=None;self.base_fcfe_0=None
        self.dcf_assumptions={'fcfe_growth_stage1_pct':[],'justification_fcfe_growth_stage1':"NG",'perpetual_growth_rate_g_pct':None,'justification_perpetual_growth_rate_g':"NG",'cost_of_equity_ke_pct':None,'justification_ke':"NG",'beta_used':None,'rfr_pct_used':self.rfr*100,'erp_pct_used':self.erp*100}
        self.multiples_assumptions={MultiplesAssumptionKeys.SELECTED_PE_VALUE:None,MultiplesAssumptionKeys.SELECTED_PE_TYPE:None,MultiplesAssumptionKeys.JUSTIFICATION_PE:"NG",MultiplesAssumptionKeys.SELECTED_EPS_VALUE:None,MultiplesAssumptionKeys.SELECTED_EPS_TYPE:None,MultiplesAssumptionKeys.JUSTIFICATION_EPS:"NG"}
        self.calculated_fve=None;self.method_used=None;self.methodology_text="Valuation process not yet run."
        self.dcf_failure_reason=None;self.multiples_failure_reason=None

    def _calculate_base_fcfe_zero(self) -> bool:
        if not self.fve_input_data or 'historical_financials' not in self.fve_input_data: self.dcf_failure_reason = "Historical financials data not available."; return False
        hist_fin = self.fve_input_data['historical_financials']
        def get_most_recent(name):dl=hist_fin.get(name,[]);return dl[0] if dl and dl[0] is not None else None
        ni,capx,da,nwc=get_most_recent('netIncome_list'),get_most_recent('capitalExpenditures_list'),get_most_recent('depreciationAndAmortizationCF_list'),get_most_recent('changeInWorkingCapital_list')
        crit={"NI":ni,"Capex":capx,"D&A":da,"NWC":nwc};miss=[k for k,v in crit.items() if v is None]
        if miss: self.dcf_failure_reason = f"Missing critical FCFE_0 inputs: {', '.join(miss)}."; return False
        try: self.base_fcfe_0=ni- (abs(capx)-da) - nwc; return True
        except TypeError as e:self.dcf_failure_reason = f"FCFE_0 calculation type error: {e}"; return False

    def _extract_json_from_response(self, llm_response: str) -> dict | None:
        m=re.search(r"```json\s*([\s\S]+?)\s*```",llm_response,re.I);js=m.group(1) if m else llm_response[llm_response.find('{'):llm_response.rfind('}')+1] if llm_response.find('{')!=-1 else None
        if not js: 
            if self.debug_mode: print("FVEAgent DEBUG: LLM response no clear JSON block for _extract_json.")
            return None
        try: return json.loads(js)
        except json.JSONDecodeError as e: 
            if self.debug_mode: print(f"FVEAgent DEBUG: _extract_json_from_response failed. Error: {e}. Snippet: {js[:100]}")
            return None

    def _summarize_financial_trends_for_llm(self, data: dict, yrs=3) -> str:
        if not data or not data.get('years'): return "No historical trends available."
        ay=min(yrs,len(data.get('years',[])));sl=[]
        if ay==0: return "No historical years data available."
        ys=data.get('years',[])[:ay]
        for k,dn in[('totalRevenue_list','Total Revenue'),('netIncome_list','Net Income'),('cashFlowFromOperations_list','Cash Flow from Operations'),('capitalExpenditures_list','Capital Expenditures')]:
            v=data.get(k,[])[:ay];td=[]
            if ys and v and len(v)==ay:
                for i in range(ay):
                    y,val=ys[i],v[i]
                    if val is not None:
                        fv=f"{val/1e9:.2f}B" if abs(val)>=1e9 else f"{val/1e6:.2f}M" if abs(val)>=1e6 else f"{val/1e3:.2f}K" if abs(val)>=1e3 else f"{val:.2f}"
                        td.append(f"{y}: {fv}")
                if td:sl.append(f"- {dn} (most recent {ay} yrs): {'; '.join(td)}")
        return "Key Historical Financial Trends:\n" + "\n".join(sl) if sl else "Limited historical financial trend data available."
        
    def _summarize_news_for_llm(self, news: list, max_h=3) -> str:
        if not news: return "No recent news headlines provided."
        vh=[item.get('title') for item in news if item.get('title') and item.get('title').strip()];
        return "Recent News Headlines Summary:\n"+"\n".join([f"- {t}" for t in vh[:max_h]]) if vh else "No valid news headlines found."

    def _generate_dcf_assumptions_with_llm(self) -> bool:
        if self.base_fcfe_0 is None: self.dcf_failure_reason = "Base FCFE_0 not calculated."; return False
        b=self.fve_input_data.get('beta');
        if b is None: self.dcf_failure_reason = "Beta not available."; return False
        try: nb=float(b);self.dcf_assumptions['beta_used']=nb
        except(ValueError,TypeError): self.dcf_failure_reason=f"Invalid Beta value: {b}. Must be numeric."; return False
        cn=self.fve_input_data.get('companyName',self.fve_input_data.get('ticker','the company'));tk=self.fve_input_data.get('ticker','N/A');sc=self.fve_input_data.get('sector','N/A')
        hf_sum=self._summarize_financial_trends_for_llm(self.fve_input_data.get('historical_financials',{}))
        n_sum=self._summarize_news_for_llm(self.fve_input_data.get('news',[]))
        ke_calc=self.rfr+nb*self.erp;ke_disp=f"{ke_calc*100:.2f}%"
        s1g_ex_list_len = self.stage1_years
        s1g_ex_example = f"a list of {s1g_ex_list_len} float percentages e.g., [{', '.join([str(round(5.0 - i * 0.5, 1)) for i in range(min(s1g_ex_list_len, 5))])}]"
        
        p=f"""AI Analyst: Provide DCF assumptions for {cn} ({tk}), Sector: {sc}. Base FCFE_0: ${self.base_fcfe_0:,.2f}. Stage 1: {s1g_ex_list_len} yrs. RFR: {self.rfr*100:.2f}%, ERP: {self.erp*100:.2f}%, Beta: {nb:.3f}, Calculated Ke: {ke_disp}. Context: {hf_sum}. {n_sum}. Task: Output a single JSON with keys: {{ "{DCFAssumptionKeys.STAGE_1_GROWTH_PCT}": ({s1g_ex_example}), "{DCFAssumptionKeys.JUSTIFICATION_STAGE_1_GROWTH}": "...", "{DCFAssumptionKeys.PERPETUAL_GROWTH_G_PCT}": "float % (e.g. 2.5)", "{DCFAssumptionKeys.JUSTIFICATION_PERPETUAL_GROWTH}": "...", "{DCFAssumptionKeys.COST_OF_EQUITY_KE_PCT}": "float % (e.g. {ke_calc*100:.2f})", "{DCFAssumptionKeys.JUSTIFICATION_KE}": "...", "{DCFAssumptionKeys.BETA_USED_IN_KE_CALC}": {nb:.3f} }}. Instructions: Percentages as floats. "{DCFAssumptionKeys.STAGE_1_GROWTH_PCT}" MUST BE A LIST OF EXACTLY {s1g_ex_list_len} NUMBERS. "{DCFAssumptionKeys.PERPETUAL_GROWTH_G_PCT}" < "{DCFAssumptionKeys.COST_OF_EQUITY_KE_PCT}" by at least {self.min_ke_g_spread_pct:.2f}%. Provide concise justifications, avoiding unnecessary repetition."""
        if self.debug_mode:print(f"\n---DCF Prompt---\n{p}\n---\n")
        try: rsp_txt=self.llm_generate_text_func(p);
        except Exception as e:self.dcf_failure_reason=f"LLM call failed (DCF assumptions): {str(e)[:100]}";return False
        if not rsp_txt: self.dcf_failure_reason="LLM returned empty response (DCF assumptions).";return False
        if self.debug_mode:print(f"\n---DCF Raw Rsp---\n{rsp_txt}\n---\n")
        pa=self._extract_json_from_response(rsp_txt)
        if not pa: self.dcf_failure_reason=self.dcf_failure_reason or "Failed to parse JSON from LLM response (DCF assumptions).";return False
        req_k=[getattr(DCFAssumptionKeys,k) for k in dir(DCFAssumptionKeys) if not k.startswith('_')]
        miss_k=[k for k in req_k if k not in pa]
        if miss_k: self.dcf_failure_reason=f"LLM DCF response missing required keys: {', '.join(miss_k)}";return False
        try:
            s1g_raw=pa[DCFAssumptionKeys.STAGE_1_GROWTH_PCT]
            if not isinstance(s1g_raw,list) or len(s1g_raw)!=s1g_ex_list_len:self.dcf_failure_reason=f"'{DCFAssumptionKeys.STAGE_1_GROWTH_PCT}' is not a list of {s1g_ex_list_len} items as requested. Got: {s1g_raw}";return False
            if not all(isinstance(g,(int,float)) for g in s1g_raw):self.dcf_failure_reason=f"'{DCFAssumptionKeys.STAGE_1_GROWTH_PCT}' contains non-numeric values.";return False
            self.dcf_assumptions['fcfe_growth_stage1_pct']=[float(g) for g in s1g_raw]
            g_pct=float(pa[DCFAssumptionKeys.PERPETUAL_GROWTH_G_PCT]);ke_pct=float(pa[DCFAssumptionKeys.COST_OF_EQUITY_KE_PCT])
            if ke_pct<=0:self.dcf_failure_reason=f"Cost of Equity (Ke={ke_pct}%) from LLM must be positive.";return False
            if g_pct>=ke_pct-self.min_ke_g_spread_pct:self.dcf_failure_reason=f"Perpetual growth ({g_pct:.2f}%) must be less than Cost of Equity ({ke_pct:.2f}%) by at least {self.min_ke_g_spread_pct:.2f}%. Current spread: {(ke_pct-g_pct):.2f}%.";return False
            self.dcf_assumptions['perpetual_growth_rate_g_pct']=g_pct;self.dcf_assumptions['cost_of_equity_ke_pct']=ke_pct
            self.dcf_assumptions['justification_fcfe_growth_stage1']=str(pa.get(DCFAssumptionKeys.JUSTIFICATION_STAGE_1_GROWTH,"N/A"))
            self.dcf_assumptions['justification_perpetual_growth_rate_g']=str(pa.get(DCFAssumptionKeys.JUSTIFICATION_PERPETUAL_GROWTH,"N/A"))
            self.dcf_assumptions['justification_ke']=str(pa.get(DCFAssumptionKeys.JUSTIFICATION_KE,"N/A"))
        except(ValueError,TypeError)as e:self.dcf_failure_reason=f"Error parsing numeric values or types from LLM DCF assumptions: {str(e)[:100]}";return False
        if self.debug_mode: print("FVEAgent DEBUG: Successfully parsed DCF assumptions from LLM.")
        return True

    def _perform_dcf_calculation(self) -> bool:
        if self.base_fcfe_0 is None:
            self.dcf_failure_reason = "Base FCFE_0 not available for DCF calculation."; return False
        
        a = self.dcf_assumptions
        if a.get('cost_of_equity_ke_pct') is None or \
           a.get('perpetual_growth_rate_g_pct') is None or \
           not a.get('fcfe_growth_stage1_pct'):
            self.dcf_failure_reason = "Missing essential DCF assumptions (Ke, g, Stage 1 growth)."; return False

        try:
            ke_d = a['cost_of_equity_ke_pct'] / 100.0
            g_d = a['perpetual_growth_rate_g_pct'] / 100.0
            s1g_d = [g / 100.0 for g in a['fcfe_growth_stage1_pct']]
        except TypeError:
            self.dcf_failure_reason = "Error converting DCF percentage assumptions to decimals (check for None types)."; return False
        except Exception as e: # Catch any other unexpected errors during conversion
            self.dcf_failure_reason = f"Unexpected error during DCF percentage conversion: {str(e)}"; return False

        if len(s1g_d) != self.stage1_years: # Check consistency
            self.dcf_failure_reason = f"Stage 1 growth rates list length ({len(s1g_d)}) mismatches configured stage1_years ({self.stage1_years})."; return False
        
        if g_d >= ke_d - self.min_ke_g_spread_decimal:
            self.dcf_failure_reason = f"Perpetual growth ({g_d*100:.2f}%) not less than Ke ({ke_d*100:.2f}%) by min spread ({self.min_ke_g_spread_decimal*100:.2f}%)."; return False

        so_raw = self.fve_input_data.get('sharesOutstanding')
        try:
            so = float(so_raw) # Attempt conversion
            if so <= 0:
                # This raise will be caught by the except block below
                raise ValueError("Shares outstanding must be positive and greater than zero.") 
        except (TypeError, ValueError) as e: # Catches float conversion errors AND the explicit raise above
            self.dcf_failure_reason = f"Shares outstanding ('{so_raw}') is invalid or not positive: {str(e)}" # Include error message from e
            if self.debug_mode: print(f"FVEAgent DEBUG: {self.dcf_failure_reason}")
            return False

        pv_s1fcfes = []; cf = self.base_fcfe_0
        if self.debug_mode: print(f"FVEAgent DEBUG DCF Calc: Base FCFE_0 = {cf:,.2f}, Ke={ke_d:.4f}, g_perp={g_d:.4f}, Stage1_Years={self.stage1_years}")

        for i in range(self.stage1_years): # Use self.stage1_years for loop range
            cf *= (1 + s1g_d[i])
            pv_fcfe_current = cf / ((1 + ke_d)**(i + 1))
            pv_s1fcfes.append(pv_fcfe_current)
            if self.debug_mode: print(f"  Year {i+1}: FCFE={cf:,.2f}, Growth={s1g_d[i]:.4f}, PV_FCFE={pv_fcfe_current:,.2f}")
        
        sum_pv_s1 = sum(pv_s1fcfes)
        fcf_tv_base = cf 
        
        tv_denom = ke_d - g_d
        if tv_denom <= 1e-9: 
            self.dcf_failure_reason = f"Terminal value denominator (Ke - g = {tv_denom:.6f}) is not sufficiently positive."; return False
        
        tv = (fcf_tv_base * (1 + g_d)) / tv_denom
        pv_tv = tv / ((1 + ke_d)**self.stage1_years) 
        
        if self.debug_mode: 
            print(f"FVEAgent DEBUG DCF Calc: Sum PV Stage 1 FCFEs = {sum_pv_s1:,.2f}")
            print(f"  TV Details: FCFE_for_TV_base={fcf_tv_base:,.2f}, TV={tv:,.2f}, PV_TV={pv_tv:,.2f}")
        
        tev = sum_pv_s1 + pv_tv
        if tev != 0 and self.debug_mode : 
            tv_weight = pv_tv / tev
            print(f"FVEAgent DEBUG DCF Calc: Terminal Value Weight = {tv_weight:.2%}")
        if self.debug_mode: print(f"FVEAgent DEBUG DCF Calc: Total Equity Value = {tev:,.2f}")

        fve_ps = tev / so
        
        if fve_ps < 0:
            self.dcf_failure_reason = f"Calculated FVE per share is negative (${fve_ps:.2f})."; return False
        
        self.calculated_fve = round(fve_ps, 2) 
        return True
    
    def _generate_multiples_assumptions_with_llm(self) -> bool:
        ttm_pe=self.fve_input_data.get('trailingPE');fwd_pe=self.fve_input_data.get('forwardPE');ttm_eps=self.fve_input_data.get('trailingEps');fwd_eps=self.fve_input_data.get('forwardEps')
        if(ttm_pe is None and fwd_pe is None)or(ttm_eps is None and fwd_eps is None):self.multiples_failure_reason="Insufficient P/E or EPS data available to generate multiples assumptions.";return False
        cn=self.fve_input_data.get('companyName',self.fve_input_data.get('ticker','the company'));tk=self.fve_input_data.get('ticker','N/A');sc=self.fve_input_data.get('sector','N/A')
        av_m_lines=["Available Company Metrics for Multiples Valuation:"];
        if ttm_pe is not None:av_m_lines.append(f"- Trailing P/E: {ttm_pe:.2f}x")
        if fwd_pe is not None:av_m_lines.append(f"- Forward P/E: {fwd_pe:.2f}x")
        if ttm_eps is not None:av_m_lines.append(f"- Trailing EPS: ${ttm_eps:.2f}")
        if fwd_eps is not None:av_m_lines.append(f"- Forward EPS: ${fwd_eps:.2f}")
        av_m_sum="\n".join(av_m_lines)
        p=f"""AI Analyst: Select P/E Multiples assumptions for {cn} ({tk}), Sector: {sc}. {av_m_sum}. Context: {self._summarize_financial_trends_for_llm(self.fve_input_data.get('historical_financials',{}))}. {self._summarize_news_for_llm(self.fve_input_data.get('news',[]))}. Task: Output single JSON: {{ "{MultiplesAssumptionKeys.SELECTED_PE_VALUE}": "float_pe (e.g. 20.5)", "{MultiplesAssumptionKeys.SELECTED_PE_TYPE}": "...", "{MultiplesAssumptionKeys.JUSTIFICATION_PE}": "...", "{MultiplesAssumptionKeys.SELECTED_EPS_VALUE}": "float_eps (e.g. 3.42)", "{MultiplesAssumptionKeys.SELECTED_EPS_TYPE}": "...", "{MultiplesAssumptionKeys.JUSTIFICATION_EPS}": "..." }}. Instructions: All numeric values as floats. Provide concise justifications, avoiding unnecessary repetition. If not feasible, values can be null."""
        if self.debug_mode:print(f"\n---Multiples Prompt---\n{p}\n---\n")
        try: rsp_txt=self.llm_generate_text_func(p);
        except Exception as e:self.multiples_failure_reason=f"LLM call failed (Multiples assumptions): {str(e)[:100]}";return False
        if not rsp_txt:self.multiples_failure_reason="LLM returned empty response (Multiples assumptions).";return False
        if self.debug_mode:print(f"\n---Multiples Raw Rsp---\n{rsp_txt}\n---\n")
        pa=self._extract_json_from_response(rsp_txt)
        if not pa:self.multiples_failure_reason=self.multiples_failure_reason or "Failed to parse JSON from LLM response (Multiples assumptions).";return False
        req_k=[getattr(MultiplesAssumptionKeys, k) for k in dir(MultiplesAssumptionKeys) if not k.startswith('_')]
        miss_k=[k for k in req_k if k not in pa]
        if miss_k:self.multiples_failure_reason=f"LLM Multiples response missing required keys: {', '.join(miss_k)}";return False
        try:
            pe_v=pa.get(MultiplesAssumptionKeys.SELECTED_PE_VALUE);eps_v=pa.get(MultiplesAssumptionKeys.SELECTED_EPS_VALUE)
            self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_PE_VALUE]=float(pe_v) if pe_v is not None else None
            self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_EPS_VALUE]=float(eps_v) if eps_v is not None else None
            if self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_PE_VALUE] is None or self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_EPS_VALUE] is None:
                self.multiples_failure_reason="LLM indicated that P/E value or EPS value for multiples valuation is not determinable or feasible."
                self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_PE_TYPE]=str(pa.get(MultiplesAssumptionKeys.SELECTED_PE_TYPE,"N/A")) # Store justifications even if values are None
                self.multiples_assumptions[MultiplesAssumptionKeys.JUSTIFICATION_PE]=str(pa.get(MultiplesAssumptionKeys.JUSTIFICATION_PE,"N/A"))
                self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_EPS_TYPE]=str(pa.get(MultiplesAssumptionKeys.SELECTED_EPS_TYPE,"N/A"))
                self.multiples_assumptions[MultiplesAssumptionKeys.JUSTIFICATION_EPS]=str(pa.get(MultiplesAssumptionKeys.JUSTIFICATION_EPS,"N/A"))
                return False
            self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_PE_TYPE]=str(pa.get(MultiplesAssumptionKeys.SELECTED_PE_TYPE,"N/A"))
            self.multiples_assumptions[MultiplesAssumptionKeys.JUSTIFICATION_PE]=str(pa.get(MultiplesAssumptionKeys.JUSTIFICATION_PE,"N/A"))
            self.multiples_assumptions[MultiplesAssumptionKeys.SELECTED_EPS_TYPE]=str(pa.get(MultiplesAssumptionKeys.SELECTED_EPS_TYPE,"N/A"))
            self.multiples_assumptions[MultiplesAssumptionKeys.JUSTIFICATION_EPS]=str(pa.get(MultiplesAssumptionKeys.JUSTIFICATION_EPS,"N/A"))
        except(ValueError,TypeError)as e:self.multiples_failure_reason=f"Error parsing numeric values (P/E or EPS) from LLM Multiples assumptions: {str(e)[:100]}";return False
        if self.debug_mode: print("FVEAgent DEBUG: Successfully parsed Multiples assumptions from LLM.")
        return True
        
    def _perform_multiples_calculation(self) -> bool:
        pe_v=self.multiples_assumptions.get(MultiplesAssumptionKeys.SELECTED_PE_VALUE);eps_v=self.multiples_assumptions.get(MultiplesAssumptionKeys.SELECTED_EPS_VALUE)
        if pe_v is None: self.multiples_failure_reason="Selected P/E multiple value is missing from assumptions."; return False
        if eps_v is None: self.multiples_failure_reason="Selected EPS value is missing from assumptions."; return False
        try: pe=float(pe_v);eps=float(eps_v)
        except(TypeError,ValueError)as e:self.multiples_failure_reason=f"Invalid P/E ({pe_v}) or EPS ({eps_v}) value type for calculation: {e}";return False
        if pe<=0:self.multiples_failure_reason=f"Selected P/E multiple ({pe:.2f}) must be positive for valuation.";return False
        fve=pe*eps
        if fve<=0:
            if self.debug_mode:print(f"FVEAgent DEBUG: Multiples Calc - EPS = {eps}, P/E = {pe} → FVE = {fve:.2f}");print(f"FVEAgent DEBUG: Multiples calc resulted in non-positive FVE.")
            self.multiples_failure_reason=f"Calculated FVE from multiples (${fve:.2f}) is not positive.";return False
        self.calculated_fve=round(fve,2)
        return True

    def _generate_final_methodology_text_with_llm(self) -> bool:
        if not self.method_used or self.method_used == "Valuation Failed":
            if self.debug_mode: print(f"FVEAgent DEBUG: Skipping LLM for methodology text as valuation method is '{self.method_used}'.")
            if not self.methodology_text or self.methodology_text=="Valuation process not yet run.": self.methodology_text = f"VALUATION_METHODOLOGY:\nValuation process failed or was not successfully completed. Method indicated: {self.method_used or 'Unknown'}."
            return False 
        
        company_identifier = self.fve_input_data.get('companyName') or self.fve_input_data.get('ticker', 'The Company') # Fix for point 1
        ticker_info = f" ({self.fve_input_data.get('ticker', 'N/A')})" if self.fve_input_data.get('companyName') and self.fve_input_data.get('ticker') else ""
        company_display = f"{company_identifier}{ticker_info}"

        fve_display = f"${self.calculated_fve:.2f}" if self.calculated_fve is not None else "N/A (Valuation Unsuccessful)"
        
        prompt_sections = ["You are an AI Financial Analyst. Your task is to generate a concise, professional 'VALUATION_METHODOLOGY:' paragraph for a stock report.",
                           "Instructions for Output:","1. Start the entire response EXACTLY with 'VALUATION_METHODOLOGY:'.","2. Present as a well-written, concise paragraph(s).","3. Be professional, clear, and suitable for inclusion in a financial report.","4. No conversational elements or self-references.","5. Clearly state the FVE and the primary method used.","6. If fallback used, state primary method's failure reason clearly.","7. For successful method, summarize key assumptions, justifications, and core calculation steps. Avoid excessive repetition in justifications.",
                           f"\nCompany Context for Methodology:",f"- Company: {company_display}",f"- Final Calculated FVE: {fve_display}",f"- Valuation Method Used: {self.method_used}"]
        
        # Helper to format failure reasons more naturally
        def format_failure_reason(reason_str: str, method_name: str) -> str:
            if not reason_str: return f"{method_name} was not completed or no specific failure reason noted."
            if "NA." in reason_str and "Shares" in reason_str and "Beta" in reason_str: return f"{method_name} valuation could not be performed due to missing Beta and Shares Outstanding data."
            if "Beta NA." in reason_str: return f"{method_name} valuation could not be performed due to missing Beta data."
            if "Shares NA." in reason_str: return f"{method_name} valuation could not be performed due to missing Shares Outstanding data."
            return f"{method_name} attempt failed: {reason_str}"

        if self.method_used == "Two-Stage FCFE DCF" or self.dcf_failure_reason:
            prompt_sections.append("\nTwo-Stage FCFE DCF Approach Details:")
            fcfe0_disp=f"${self.base_fcfe_0:,.2f}" if self.base_fcfe_0 is not None else "N/A";prompt_sections.append(f"- Base FCFE (FCFE_0): {fcfe0_disp}")
            dcf_a=self.dcf_assumptions;ke_disp=f"{dcf_a['cost_of_equity_ke_pct']:.2f}%" if dcf_a.get('cost_of_equity_ke_pct')is not None else"N/A";beta_disp=f"{dcf_a['beta_used']:.3f}" if dcf_a.get('beta_used')is not None else"N/A";rfr_disp=f"{dcf_a['rfr_pct_used']:.1f}%";erp_disp=f"{dcf_a['erp_pct_used']:.1f}%"
            prompt_sections.append(f"- Cost of Equity (Ke): {ke_disp} (Beta: {beta_disp}, RFR: {rfr_disp}, ERP: {erp_disp})");prompt_sections.append(f"  - Ke Justification: {dcf_a.get('justification_ke','N/A')}")
            s1_g_list=dcf_a.get('fcfe_growth_stage1_pct',[]);s1_growth_disp=', '.join([f"{g:.1f}%" for g in s1_g_list])if s1_g_list else"N/A"
            prompt_sections.append(f"- Stage 1 FCFE Growth Rates ({self.stage1_years} yrs): [{s1_growth_disp}]");prompt_sections.append(f"  - Stage 1 Growth Justification: {dcf_a.get('justification_fcfe_growth_stage1','N/A')}")
            g_perp_disp=f"{dcf_a['perpetual_growth_rate_g_pct']:.2f}%" if dcf_a.get('perpetual_growth_rate_g_pct')is not None else"N/A"
            prompt_sections.append(f"- Perpetual Growth Rate (g): {g_perp_disp}");prompt_sections.append(f"  - Perpetual Growth Justification: {dcf_a.get('justification_perpetual_growth_rate_g','N/A')}")
            if self.method_used=="Two-Stage FCFE DCF":prompt_sections.append("- DCF Calculation Summary: FCFEs were projected for Stage 1, a terminal value was calculated using the Gordon Growth Model, all cash flows were discounted to present value and summed for total equity value, then divided by shares outstanding.")
            elif self.dcf_failure_reason: prompt_sections.append(f"- {format_failure_reason(self.dcf_failure_reason, 'DCF')}")
        
        if self.method_used == "P/E Multiples-Based" or (self.dcf_failure_reason and self.multiples_failure_reason is not None):
            prompt_sections.append("\nP/E Multiples-Based Approach Details:")
            mult_a=self.multiples_assumptions;pe_val_disp=f"{mult_a.get(MultiplesAssumptionKeys.SELECTED_PE_VALUE):.1f}x" if mult_a.get(MultiplesAssumptionKeys.SELECTED_PE_VALUE)is not None else"N/A";pe_type_disp=mult_a.get(MultiplesAssumptionKeys.SELECTED_PE_TYPE,"N/A")
            prompt_sections.append(f"- Selected P/E Multiple: {pe_val_disp} ({pe_type_disp})");prompt_sections.append(f"  - P/E Justification: {mult_a.get(MultiplesAssumptionKeys.JUSTIFICATION_PE,'N/A')}")
            eps_val_disp=f"${mult_a.get(MultiplesAssumptionKeys.SELECTED_EPS_VALUE):.2f}" if mult_a.get(MultiplesAssumptionKeys.SELECTED_EPS_VALUE)is not None else"N/A";eps_type_disp=mult_a.get(MultiplesAssumptionKeys.SELECTED_EPS_TYPE,"N/A")
            prompt_sections.append(f"- Selected EPS: {eps_val_disp} ({eps_type_disp})");prompt_sections.append(f"  - EPS Justification: {mult_a.get(MultiplesAssumptionKeys.JUSTIFICATION_EPS,'N/A')}")
            if self.method_used=="P/E Multiples-Based":prompt_sections.append("- Multiples Calculation Summary: FVE was calculated as Selected P/E Multiple multiplied by Selected EPS.")
            elif self.multiples_failure_reason: prompt_sections.append(f"- {format_failure_reason(self.multiples_failure_reason, 'Multiples')}")
        
        final_prompt="\n".join(prompt_sections)
        if self.debug_mode: print(f"\n---Methodology LLM Prompt---\n{final_prompt}\n---\n")
        try:
            llm_response = self.llm_generate_text_func(final_prompt)
            if not llm_response or not llm_response.strip(): self.methodology_text = "VALUATION_METHODOLOGY:\nLLM explanation for methodology was empty."; return False
            self.methodology_text = f"VALUATION_METHODOLOGY:\n{llm_response.strip()}" if not llm_response.strip().upper().startswith("VALUATION_METHODOLOGY:") else llm_response.strip()
            if self.debug_mode: print(f"\n---Methodology LLM Raw Rsp---\n{self.methodology_text}\n---\n")
            return True
        except Exception as e: self.methodology_text = f"VALUATION_METHODOLOGY:\nError generating methodology explanation: {str(e)[:100]}"; return False
    
    def run_valuation_process(self, fve_input_data: dict) -> tuple[float | None, str]:
        self._reset_internal_state(); self.fve_input_data = fve_input_data
        company_identifier = self.fve_input_data.get('companyName') or self.fve_input_data.get('ticker', 'The Company')
        ticker_info = f" ({self.fve_input_data.get('ticker', 'N/A')})" if self.fve_input_data.get('companyName') and self.fve_input_data.get('ticker') else ""
        company_display_name = f"{company_identifier}{ticker_info}"

        dcf_ok=False; b=self.fve_input_data.get('beta')
        current_dcf_fail_parts = []
        if b is None: current_dcf_fail_parts.append("Beta missing")
        else:
            try:float(b)
            except(ValueError,TypeError):current_dcf_fail_parts.append(f"Beta '{b}' not numeric")
        if not self.fve_input_data.get('sharesOutstanding'): current_dcf_fail_parts.append("Shares Outstanding missing")
        if current_dcf_fail_parts: self.dcf_failure_reason = ", ".join(current_dcf_fail_parts) + "."
        
        if not self.dcf_failure_reason:
            if self._calculate_base_fcfe_zero():
                if self.base_fcfe_0 is not None:
                    if self._generate_dcf_assumptions_with_llm():
                        if self._perform_dcf_calculation():self.method_used="Two-Stage FCFE DCF";dcf_ok=True
        if not dcf_ok:
            if self._generate_multiples_assumptions_with_llm():
                if self.multiples_assumptions.get(MultiplesAssumptionKeys.SELECTED_PE_VALUE) is not None and \
                   self.multiples_assumptions.get(MultiplesAssumptionKeys.SELECTED_EPS_VALUE) is not None:
                    if self._perform_multiples_calculation(): self.method_used = "P/E Multiples-Based"
        
        if self.calculated_fve is not None: # A method succeeded
            if not self._generate_final_methodology_text_with_llm() and (not self.methodology_text or self.methodology_text=="Valuation process not yet run."):
                 self.methodology_text = f"VALUATION_METHODOLOGY:\nThe FVE for {company_display_name} was calculated as ${self.calculated_fve:.2f} using the {self.method_used} method. A detailed LLM-generated explanation for the methodology was not available."
        else: # All methods failed or FVE was None
            self.method_used = "Valuation Failed" # Ensure method_used reflects complete failure
            dcf_reason_formatted = f"DCF valuation could not be performed due to: {self.dcf_failure_reason}." if self.dcf_failure_reason else "DCF valuation was not successfully completed."
            multiples_reason_formatted = f"Multiples valuation could not be performed due to: {self.multiples_failure_reason}." if self.multiples_failure_reason else "Multiples valuation was not successfully completed or attempted."
            
            if self.dcf_failure_reason and self.multiples_failure_reason:
                self.methodology_text = f"VALUATION_METHODOLOGY:\nValuation for {company_display_name} failed. {dcf_reason_formatted} {multiples_reason_formatted}"
            elif self.dcf_failure_reason: # Only DCF failed, and Multiples wasn't run or also implicitly failed to produce FVE
                self.methodology_text = f"VALUATION_METHODOLOGY:\nValuation for {company_display_name} failed. {dcf_reason_formatted}"
            elif self.multiples_failure_reason: # DCF passed initial checks but didn't yield FVE, and Multiples also failed
                self.methodology_text = f"VALUATION_METHODOLOGY:\nValuation for {company_display_name} failed. {multiples_reason_formatted}"
            else: # Should ideally not happen if a failure reason is always set
                self.methodology_text = f"VALUATION_METHODOLOGY:\nValuation for {company_display_name} could not be completed due to unspecified reasons."
        
        if self.debug_mode:
            fve_disp = f"{self.calculated_fve:.2f}" if self.calculated_fve is not None else "N/A"
            print(f"FVEAgent DEBUG: Valuation process completed for {company_display_name}. Method: {self.method_used or 'Failed'}, FVE: {fve_disp}")
        return self.calculated_fve, self.methodology_text