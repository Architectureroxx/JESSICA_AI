Set sapi = CreateObject("SAPI.SpVoice")
Set sapi.Voice = sapi.GetVoices.Item(0)
sapi.Speak "Powering down console modules. Goodbye, Master Archit."
