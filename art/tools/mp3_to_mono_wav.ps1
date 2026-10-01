# Decodes an MP3 with the game's own decoder (MP3Sharp.dll) and writes a mono 16-bit WAV.
# OpenRA only positions mono sounds on the map; stereo sounds play at full volume everywhere.
#
# Usage: pwsh mp3_to_mono_wav.ps1 <in.mp3> <out.wav>
param([Parameter(Mandatory)][string]$In, [Parameter(Mandatory)][string]$Out)

$game = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Add-Type -Path (Join-Path $game "MP3Sharp.dll")

$mp3 = [MP3Sharp.MP3Stream]::new((Resolve-Path $In).Path)

# The decoder's output format decides the layout: it writes two channels even for a mono source.
$channels = if ($mp3.Format -eq [MP3Sharp.SoundFormat]::Pcm16BitStereo) { 2 } else { 1 }
$rate = $mp3.Frequency
$pcm = [System.IO.MemoryStream]::new()
$buffer = [byte[]]::new(65536)
while (($n = $mp3.Read($buffer, 0, $buffer.Length)) -gt 0) { $pcm.Write($buffer, 0, $n) }
$mp3.Dispose()
$bytes = $pcm.ToArray()

if ($channels -eq 2) {
    $frames = [int][Math]::Floor($bytes.Length / 4)
    $mono = [byte[]]::new($frames * 2)
    for ($i = 0; $i -lt $frames; $i++) {
        $l = [BitConverter]::ToInt16($bytes, $i * 4)
        $r = [BitConverter]::ToInt16($bytes, $i * 4 + 2)
        $m = [int16][Math]::Round(($l + $r) / 2.0)
        $mono[$i * 2] = [byte]($m -band 0xFF)
        $mono[$i * 2 + 1] = [byte](($m -shr 8) -band 0xFF)
    }
    $bytes = $mono
}

$fs = [System.IO.File]::Create($Out)
$w = [System.IO.BinaryWriter]::new($fs)
$w.Write([System.Text.Encoding]::ASCII.GetBytes("RIFF")); $w.Write([int](36 + $bytes.Length))
$w.Write([System.Text.Encoding]::ASCII.GetBytes("WAVEfmt ")); $w.Write([int]16)
$w.Write([int16]1); $w.Write([int16]1); $w.Write([int]$rate); $w.Write([int]($rate * 2))
$w.Write([int16]2); $w.Write([int16]16)
$w.Write([System.Text.Encoding]::ASCII.GetBytes("data")); $w.Write([int]$bytes.Length)
$w.Write($bytes)
$w.Dispose(); $fs.Dispose()

"{0}: {1} ch, {2} Hz, {3:N1} s -> mono WAV {4:N0} bytes" -f (Split-Path $In -Leaf), $channels, $rate, ($bytes.Length / 2.0 / $rate), $bytes.Length
