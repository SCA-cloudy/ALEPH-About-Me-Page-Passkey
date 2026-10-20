// 패스키가 보내는 값(attestationObject, 공개키)을 읽기 위한 최소한의 CBOR 해석기입니다.
// 필요한 것만 지원합니다: 정수, 바이트열, 글자, 배열, 맵, true/false/null. (부동소수·무한 길이는 거절)

export function decodeCbor(buf, offset = 0) {
  const [value, end] = decodeItem(buf, offset);
  return { value, end };
}

function readArg(buf, off, ai) {
  if (ai < 24) return [ai, off];
  if (ai === 24) return [buf[off], off + 1];
  if (ai === 25) return [buf.readUInt16BE(off), off + 2];
  if (ai === 26) return [buf.readUInt32BE(off), off + 4];
  throw new Error("cbor: unsupported length");
}

function decodeItem(buf, off) {
  if (off >= buf.length) throw new Error("cbor: truncated");
  const ib = buf[off++];
  const major = ib >> 5;
  const ai = ib & 31;
  if (major === 7) {
    if (ai === 20) return [false, off];
    if (ai === 21) return [true, off];
    if (ai === 22 || ai === 23) return [null, off];
    throw new Error("cbor: unsupported simple value");
  }
  let arg;
  [arg, off] = readArg(buf, off, ai);
  switch (major) {
    case 0:
      return [arg, off];
    case 1:
      return [-1 - arg, off];
    case 2:
      if (off + arg > buf.length) throw new Error("cbor: truncated");
      return [buf.subarray(off, off + arg), off + arg];
    case 3:
      if (off + arg > buf.length) throw new Error("cbor: truncated");
      return [buf.subarray(off, off + arg).toString("utf8"), off + arg];
    case 4: {
      const arr = [];
      for (let i = 0; i < arg; i++) {
        let v;
        [v, off] = decodeItem(buf, off);
        arr.push(v);
      }
      return [arr, off];
    }
    case 5: {
      const map = new Map();
      for (let i = 0; i < arg; i++) {
        let k, v;
        [k, off] = decodeItem(buf, off);
        [v, off] = decodeItem(buf, off);
        map.set(k, v);
      }
      return [map, off];
    }
    case 6:
      return decodeItem(buf, off); // 태그는 무시하고 안의 값만 사용
    default:
      throw new Error("cbor: unsupported type");
  }
}
