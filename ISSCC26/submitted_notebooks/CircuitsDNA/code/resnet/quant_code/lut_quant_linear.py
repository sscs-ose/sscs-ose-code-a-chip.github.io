import torch
import torch.nn.functional as F

from sym_quant import QuantLinear
from lut_quant_conv import Int8LUTMultiplier


class LUTQuantLinear(QuantLinear):
    """Linear layer that replaces int8 multiplications with an LUT lookup."""

    def __init__(
        self,
        *args,
        lut_table: torch.Tensor | None = None,
        mini_batch_size: int = 0,
        mini_out_features: int = 0,
        **kwargs,
    ):
        self.mini_batch_size = int(max(mini_batch_size, 0))
        self.mini_out_features = int(max(mini_out_features, 0))
        super().__init__(*args, **kwargs)
        if self.nbits_weight != 8:
            raise ValueError("LUTQuantLinear currently supports 8-bit weights only")
        if self.nbits_act is not None and self.nbits_act != 8:
            raise ValueError("LUTQuantLinear currently supports 8-bit activations only")
        self.multiplier = Int8LUTMultiplier(lut_table)

    def forward(self, x: torch.Tensor, *, collect: bool = False):
        x_processed = x
        if self.act_in_quant is not None:
            x_processed = self.act_in_quant(x, collect=collect)

        bias = super()._quantize_bias()
        w_float = super()._quantize_weight()

        if collect:
            y = self._forward_fallback(x_processed, w_float, bias)
        else:
            self._assert_scale_ready()
            x_int, act_scale = self._quantize_activation_to_int(x_processed)
            w_int, w_scales = self._quantize_weight_to_int(w_float)
            if x_int is None or w_int is None or w_scales is None:
                raise RuntimeError("LUTQuantLinear: missing integer representation after quantization")
            y_lut = self._linear_lut(x_int, w_int, act_scale, w_scales, bias)
            y_surrogate = F.linear(x_processed, w_float, bias)
            y = y_lut + (y_surrogate - y_surrogate.detach())

        if self.act_out_quant is not None:
            y = self.act_out_quant(y, collect=collect)
        return y

    def _forward_fallback(self, x_processed, w_float, bias):
        return F.linear(x_processed, w_float, bias)

    def _assert_scale_ready(self) -> None:
        if self.act_in_quant is None:
            raise RuntimeError("LUTQuantLinear: input quantizer is disabled")
        if self.act_in_quant.scale is None:
            raise RuntimeError("LUTQuantLinear: activation scale is not calibrated")
        if self.w_quant is None or self.w_quant.scale is None:
            raise RuntimeError("LUTQuantLinear: weight scale is not calibrated")

    @staticmethod
    def _q_bounds(nbits: int) -> tuple[int, int]:
        qmin = -(2 ** (nbits - 1))
        qmax = (2 ** (nbits - 1)) - 1
        return qmin, qmax

    @staticmethod
    def _ensure_scalar(scale, device) -> float:
        if scale is None:
            raise ValueError("scale must not be None")
        if torch.is_tensor(scale):
            return float(scale.detach().to(device=device).item())
        return float(scale)

    def _quantize_activation_to_int(self, x_q: torch.Tensor): # The pseudo-quantized value remains as a float. It is generated into an accurate int8 (int 16 for not overflow (int8 + 128)) code value through division by "scale" and rounding.
        if self.act_in_quant is None or self.act_in_quant.scale is None:
            return None, None
        scale_val = self._ensure_scalar(self.act_in_quant.scale, x_q.device)
        qmin, qmax = self._q_bounds(self.nbits_act)
        x_int = torch.round(x_q / scale_val).clamp(qmin, qmax).to(torch.int16)
        return x_int, scale_val

    def _quantize_weight_to_int(self, w_float: torch.Tensor | None = None):
        qmin, qmax = self._q_bounds(self.nbits_weight)
        if self.w_quant is None or self.w_quant.scale is None:
            return None, None
        target = self.weight if w_float is None else w_float
        scale_val = self._ensure_scalar(self.w_quant.scale, target.device)
        w_int = torch.round(target / scale_val).clamp(qmin, qmax).to(torch.int16)
        return w_int, torch.tensor([scale_val], device=target.device, dtype=torch.float32)

    def _linear_lut(
        self,
        x_int: torch.Tensor,
        w_int: torch.Tensor,
        act_scale: float,
        weight_scales: torch.Tensor,
        bias: torch.Tensor | None,
    ) -> torch.Tensor:
        orig_shape = x_int.shape
        in_features = orig_shape[-1]
        flat_x = x_int.reshape(-1, in_features)
        out_features = w_int.shape[0]

        scales = weight_scales.to(dtype=torch.float32, device=x_int.device)
        if scales.numel() == 1:
            scales = scales.expand(out_features)
        else:
              torch._assert(scales.numel() == out_features, "weight scale shape mismatch")
        scales = scales * float(act_scale)

        table = self.multiplier.table.to(device=x_int.device, dtype=torch.int16)
        x_idx = (flat_x.to(torch.int32) + 128).clamp_(0, 255).to(torch.long)
        w_idx = (w_int.to(torch.int32) + 128).clamp_(0, 255).to(torch.long)

        B = x_idx.shape[0]
        mini_batch = self.mini_batch_size or B
        mini_out = self.mini_out_features or out_features

        acc_buffer = torch.zeros(B, out_features, dtype=torch.float32, device=x_int.device)

        for b_start in range(0, B, mini_batch):
            b_end = min(b_start + mini_batch, B)
            x_chunk = x_idx[b_start:b_end]  # [Bchunk, K]
            for o_start in range(0, out_features, mini_out):
                o_end = min(o_start + mini_out, out_features)
                w_chunk = w_idx[o_start:o_end]  # [Ochunk, K]

                x_sel = x_chunk.unsqueeze(1).expand(-1, w_chunk.size(0), -1)
                w_sel = w_chunk.unsqueeze(0).expand(b_end - b_start, -1, -1)
                prod = table[x_sel, w_sel].to(torch.int32)
                acc = prod.sum(dim=2)
                acc_buffer[b_start:b_end, o_start:o_end] = acc.to(torch.float32)

        acc_buffer *= scales.view(1, -1)
        if bias is not None:
            acc_buffer += bias.view(1, -1).to(acc_buffer.dtype)

        out_shape = tuple(orig_shape[:-1]) + (out_features,)
        return acc_buffer.view(out_shape)
