from pathsim.blocks import Block
from pathsim.events.schedule import Schedule
from pathsim.events.condition import Condition
import math
import numpy as np

class CRSAR(Block):

    input_port_labels  = {"vinp": 0, "vinn": 1, "voffp": 2, "voffn": 3, "samp_en": 4}
    output_port_labels = {"vout": 0, "dout": 1, "done": 2, "vcp": 3, 
                          "vcn": 4, "vcout": 5, "vinp_samp": 6, "vinn_samp": 7, 
                          "dout_raw": 8}

    def __init__(self, n_bits=8, weights=None, vref=1.0, T=1.0, tau=0.0, 
                 estimated_weights=None, comp_offset=0, comp_noise_rms=0, 
                 total_sampling_cap=0, settling_error_pct=0, seed=1):
        super().__init__()

        self.n_bits = n_bits
        self.vref   = vref
        self.T      = T
        self.tau    = tau
        self.comp_offset = comp_offset
        self.comp_noise_rms = comp_noise_rms
        self.settling_error_pct = settling_error_pct
        self.total_sampling_cap = total_sampling_cap

        # Binary capacitor weights unless otherwise specified
        self.weights = weights if weights is not None else self._default_weights()

        # if estimated weights not specified, assume they are ideal
        self.estimated_weights = estimated_weights \
            if estimated_weights is not None else self.weights 
        
        # Internal SAR state
        self._ndecisions = len(self.weights)
        self._decisions = [0] * self._ndecisions
        self._step = 0
        self._comp_pos = 0.0
        self._comp_neg = 0.0
        self._comp_pos_unsettled = 0.0
        self._comp_neg_unsettled = 0.0
        self._comp_out = 0
        self._vinp_samp = 0.0
        self._vinn_samp = 0.0
        self._done = 0
        self._rng = np.random.default_rng(seed=seed)

        t_bit = T / (self._ndecisions + 2)

        def _clock(t):
            done_idx = self.output_port_labels['done']
            vcp_idx = self.output_port_labels['vcp']
            vcn_idx = self.output_port_labels['vcn']
            vcout_idx = self.output_port_labels['vcout']

            if self._step == 0:
                self._sample(t)
            elif self._step == self._ndecisions + 1:
                self._update_conv_results(t)
            else:
                self._convert(t)

            if self._step == self._ndecisions + 1:
                self._step = 0
            else:
                self._step += 1

            self.outputs[vcp_idx] = self._comp_pos_unsettled
            self.outputs[vcn_idx] = self._comp_neg_unsettled
            self.outputs[vcout_idx] = self._comp_out
            self.outputs[done_idx] = self._done

        self.events = [
            Schedule(t_start=tau, t_period=t_bit, func_act=_clock)
        ]

    # ------------------------------------------------------------------
    # Internal clock handlers
    # ------------------------------------------------------------------

    def _update_conv_results(self, t):
        vout_idx = self.output_port_labels['vout']
        dout_idx = self.output_port_labels['dout']
        vinp_samp_idx = self.output_port_labels['vinp_samp']
        vinn_samp_idx = self.output_port_labels['vinn_samp']
        dout_raw_idx = self.output_port_labels['dout_raw']
        
        self._done = 1

        # calculate conversion result (between -1 and 1)
        result = 0
        for i in range(0, len(self.estimated_weights)):
            result += self.estimated_weights[i] * (2 * self._decisions[i] - 1)

        # convert to -vref to vref
        self.outputs[vout_idx] = result * self.vref

        # convert to 0 -> 2**n
        # example: result = 0.75 (=0.5 + 0.25), N=2
        # -> should map to 0b11 (3)
        # floor[(1.75/2)*4] = 3
        self.outputs[dout_idx] = math.floor(0.5*(result + 1) * (2 ** self.n_bits))

        # calculate binary integer representation of raw decisions
        raw_sum = 0
        for i, d in enumerate(self._decisions):
            raw_sum += (2 ** (self._ndecisions - 1 - i)) * d

        self.outputs[dout_raw_idx] = raw_sum

        # update the input signal used to prooduce result
        self.outputs[vinp_samp_idx] = self._vinp_samp
        self.outputs[vinn_samp_idx] = self._vinn_samp

    def _sample(self, t):
        samp_noise_p = 0
        samp_noise_n = 0
        # determine if new input should be sampled
        samp_en_idx = self.input_port_labels["samp_en"]
        if self.inputs[samp_en_idx]:
            if self.total_sampling_cap > 0:
                k_boltzmann = 1.38e-23
                temp_kelvin = 300
                kTC_std_deviation = math.sqrt(k_boltzmann*temp_kelvin/self.total_sampling_cap)
                samp_noise_p = self._rng.normal(0, kTC_std_deviation, 1)[0]
                samp_noise_n = self._rng.normal(0, kTC_std_deviation, 1)[0]
            
            # read inputs
            vinp_idx = self.input_port_labels['vinp']
            vinn_idx = self.input_port_labels['vinn']
            self._vinp_samp = self.inputs[vinp_idx]
            self._vinn_samp = self.inputs[vinn_idx]

        # read offset and compute initial comparator input
        voffp_idx = self.input_port_labels["voffp"]
        voffn_idx = self.input_port_labels["voffn"]
        voffp = self.inputs[voffp_idx]
        voffn = self.inputs[voffn_idx]
        self._comp_pos = self._vinp_samp + samp_noise_p + voffp
        self._comp_neg = self._vinn_samp + samp_noise_n + voffn

        # assume perfect settling for initial sampling
        self._comp_pos_unsettled = self._comp_pos
        self._comp_neg_unsettled = self._comp_neg

        self._done = 0

    def _convert(self, t):
        self._comp_out = self._compare(t)
        bit_idx = self._step - 1
        self._decisions[bit_idx] = self._comp_out

        # comparator output = 1 -> DAC voltage should decrease
        next_comp_pos = self._comp_pos - \
            (2 * self._comp_out - 1) * self.weights[bit_idx] * (self.vref/2)
        next_comp_neg = self._comp_neg + \
            (2 * self._comp_out - 1) * self.weights[bit_idx] * (self.vref/2)

        # computed "unsettled" comparator input for next comparison
        # settling error is differential (half in +, half in -)
        self._comp_pos_unsettled = self._comp_pos + \
            (next_comp_pos - self._comp_pos) * (1 - (0.5 * self.settling_error_pct / 100))
        self._comp_neg_unsettled = self._comp_neg + \
            (next_comp_neg - self._comp_neg) * (1 - (0.5 * self.settling_error_pct / 100))

        # update comparator input
        self._comp_pos = next_comp_pos
        self._comp_neg = next_comp_neg

        self._done = 0

    def _compare(self, t):
        # get Gaussian noise sample for comparator noise
        comp_noise_rms = self._rng.normal(0, self.comp_noise_rms, 1)[0]

        # add offset/noise to comparator input and return result (added to [+] input)
        comp_p_total = self._comp_pos_unsettled + self.comp_offset + comp_noise_rms
        if comp_p_total > self._comp_neg_unsettled:
            return 1

        return 0

    def _default_weights(self):
        return [0.5 ** i for i in range(1, self.n_bits + 1)]
    
    # ------------------------------------------------------------------
    # Pathsim protocol
    # ------------------------------------------------------------------

    def __len__(self):
        # No algebraic feedthrough: outputs change only on discrete clock events
        return 0

class CRSARCtrlODC(Block):
    input_port_labels  = {"sar_done": 0, "sar_dout": 1, "sar_dout_raw": 2}
    output_port_labels = {"odc_dout_offsetp": 0, "odc_dout_offsetn": 1, 
                          "odc_state": 2, "sar_samp_en": 3, "sar_vinp_offset": 4, 
                          "sar_vinn_offset": 5, "odc_dout_raw_offsetp": 6, 
                          "odc_dout_raw_offsetn": 7}

    def __init__(self, analog_offset=0, tau=0):
        super().__init__()

        self.analog_offset = analog_offset
        self.tau = 0

        # internal state
        self._odc_dout_offsetp = 0
        self._odc_dout_offsetn = 0
        self._odc_dout_raw_offsetp = 0
        self._odc_dout_raw_offsetn = 0
        self._odc_state = 0 # state=0 -> offset is positive
        self._sar_samp_en = 1 # sample input in state=0, disabled in state=1
        self._sar_vinp_offset = self.analog_offset/2
        self._sar_vinn_offset = -self.analog_offset/2

        def _start(t):
            self._update_outputs()
            self._reset_odc_ctrl_act(t)

        self.events = [Schedule(t_start=tau, t_end=tau, func_act=_start)]

    def _reset_odc_ctrl_evt(self, t):
        sar_done_idx = self.input_port_labels["sar_done"]
        return self.inputs[sar_done_idx] < 0.5
    
    def _reset_odc_ctrl_act(self, t):
        self.events = [Condition(func_evt=self._update_odc_ctrl_evt, func_act=self._update_odc_ctrl_act)]

    def _update_odc_ctrl_evt(self, t):
        sar_done_idx = self.input_port_labels["sar_done"]
        return self.inputs[sar_done_idx] > 0.5
    
    def _update_odc_ctrl_act(self, t):
        sar_dout_idx = self.input_port_labels["sar_dout"]
        sar_dout = self.inputs[sar_dout_idx]
        sar_dout_raw_idx = self.input_port_labels["sar_dout_raw"]
        sar_dout_raw = self.inputs[sar_dout_raw_idx]

        if self._odc_state == 0:
            self._odc_dout_offsetp = sar_dout
            self._odc_dout_raw_offsetp = sar_dout_raw
            self._sar_samp_en = 0
            self._sar_vinp_offset = -self.analog_offset/2
            self._sar_vinn_offset = self.analog_offset/2
            self._odc_state = 1
        else:
            self._odc_dout_offsetn = sar_dout
            self._odc_dout_raw_offsetn = sar_dout_raw
            self._sar_samp_en = 1
            self._sar_vinp_offset = self.analog_offset/2
            self._sar_vinn_offset = -self.analog_offset/2
            self._odc_state = 0
        
        self._update_outputs()
        self.events = [Condition(func_evt=self._reset_odc_ctrl_evt, func_act=self._reset_odc_ctrl_act)]

    def _update_outputs(self):
        odc_dout_offsetp_idx = self.output_port_labels["odc_dout_offsetp"]
        odc_dout_offsetn_idx = self.output_port_labels["odc_dout_offsetn"]
        odc_state_idx = self.output_port_labels["odc_state"]
        sar_samp_en_idx = self.output_port_labels["sar_samp_en"]
        sar_vinp_offset_idx = self.output_port_labels["sar_vinp_offset"]
        sar_vinn_offset_idx = self.output_port_labels["sar_vinn_offset"]
        odc_dout_raw_offsetp_idx = self.output_port_labels["odc_dout_raw_offsetp"]
        odc_dout_raw_offsetn_idx = self.output_port_labels["odc_dout_raw_offsetn"]

        self.outputs[odc_dout_offsetp_idx] = self._odc_dout_offsetp
        self.outputs[odc_dout_offsetn_idx] = self._odc_dout_offsetn
        self.outputs[odc_state_idx] = self._odc_state
        self.outputs[sar_samp_en_idx] = self._sar_samp_en
        self.outputs[sar_vinp_offset_idx] = self._sar_vinp_offset
        self.outputs[sar_vinn_offset_idx] = self._sar_vinn_offset
        self.outputs[odc_dout_raw_offsetp_idx] = self._odc_dout_raw_offsetp
        self.outputs[odc_dout_raw_offsetn_idx] = self._odc_dout_raw_offsetn

    # ------------------------------------------------------------------
    # Pathsim protocol
    # ------------------------------------------------------------------

    def __len__(self):
        # No algebraic feedthrough: outputs change only on discrete clock events
        return 0