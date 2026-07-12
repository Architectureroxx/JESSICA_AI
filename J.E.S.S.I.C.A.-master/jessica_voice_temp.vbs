Set sapi = CreateObject("SAPI.SpVoice")
Set sapi.Voice = sapi.GetVoices.Item(1)
sapi.Rate = 1
sapi.Speak "Powering down console modules. Goodbye, Master Utkrisht."
